#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.experiment_controls import read_controls
from axm_uc.neural_experience_transport import paths as neural_paths, read_jsonl
from axm_uc.neural_growth import inspect_model_state, write_growth_comparison


class ExperimentError(RuntimeError):
    pass


def _run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
    if check and completed.returncode != 0:
        raise ExperimentError(f"command failed ({completed.returncode}): {' '.join(command)}")
    return completed


def _waldo_binary(explicit: str | None, state: Path, *, build_if_missing: bool) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        if not candidate.is_file():
            raise ExperimentError(f"WALDO binary not found: {candidate}")
        return candidate
    found = shutil.which("waldo")
    if found:
        return Path(found).resolve()
    suffix = ".exe" if os.name == "nt" else ""
    local = state / "bin" / f"waldo{suffix}"
    if local.is_file():
        return local
    if not build_if_missing:
        raise ExperimentError("WALDO binary not found; pass --waldo or allow the launcher to build it")
    go = shutil.which("go")
    if not go:
        raise ExperimentError("WALDO binary is missing and Go is not installed or not on PATH")
    local.parent.mkdir(parents=True, exist_ok=True)
    print(f"Building OpenWALDO -> {local}")
    _run([go, "build", "-o", str(local), "./cmd/waldo"], cwd=ROOT / "neural" / "waldo")
    return local


def _experiment_layout(state: Path) -> dict[str, Path]:
    local = state / "openwaldo-local"
    return {
        "base": local,
        "config": local / "config.json",
        "index": local / "index",
        "lookaside": local / "lookaside",
        "models": local / "models",
        "batches": local / "batches",
        "db": local / "feed.sqlite3",
        "status": local / "STATUS.json",
    }


def _waldo_env(config: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["WALDO_CONFIG"] = str(config)
    return env


def _configure_waldo(waldo: Path, layout: dict[str, Path], backend: str) -> dict[str, str]:
    layout["base"].mkdir(parents=True, exist_ok=True)
    layout["lookaside"].mkdir(parents=True, exist_ok=True)
    layout["models"].mkdir(parents=True, exist_ok=True)
    layout["batches"].mkdir(parents=True, exist_ok=True)
    env = _waldo_env(layout["config"])
    if not (layout["index"] / "index.yaml").is_file():
        _run([str(waldo), "index", "init", str(layout["index"])], env=env)
    for key, value in (
        ("index", str(layout["index"])),
        ("lookaside", layout["lookaside"].resolve().as_uri()),
        ("model.root", str(layout["models"])),
        ("model.backend", backend),
    ):
        _run([str(waldo), "config", "set", key, value], env=env)
    return env


def _connection(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS consumed (
            event_id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            trained_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def _new_intake_rows(connection: sqlite3.Connection, intake: Path, maximum: int, minimum_sequence: int = 0) -> list[dict[str, Any]]:
    if not intake.is_file():
        return []
    consumed = {row[0] for row in connection.execute("SELECT event_id FROM consumed")}
    rows: list[dict[str, Any]] = []
    for row in read_jsonl(intake):
        meta = row.get("axm") if isinstance(row.get("axm"), dict) else {}
        event_id = str(meta.get("event_id", ""))
        sequence = meta.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence <= minimum_sequence:
            continue
        if not event_id or event_id in consumed or not isinstance(row.get("text"), str):
            continue
        rows.append(row)
        if len(rows) >= maximum:
            break
    return rows


def _batch_identity(rows: list[dict[str, Any]]) -> str:
    ids = [str(row["axm"]["event_id"]) for row in rows]
    body = json.dumps(ids, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _write_batch(layout: dict[str, Path], rows: list[dict[str, Any]], batch_id: str) -> Path:
    target = layout["batches"] / f"{batch_id}.jsonl"
    with target.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(
                json.dumps(
                    {"text": row["text"], "axm": row["axm"]},
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
    return target


def _model_exists(waldo: Path, env: dict[str, str], name: str) -> bool:
    return _run([str(waldo), "model", "summary", name], env=env, check=False).returncode == 0


def _corpus_exists(waldo: Path, env: dict[str, str], destination: str) -> bool:
    return _run([str(waldo), "index", "show", destination], env=env, check=False).returncode == 0


def _write_status(layout: dict[str, Path], value: dict[str, Any]) -> None:
    layout["status"].write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def feed_once(
    *,
    waldo: Path,
    env: dict[str, str],
    layout: dict[str, Path],
    model_name: str,
    preset: str,
    maximum: int,
    batch_size: int,
    learning_rate: float,
) -> bool:
    intake = neural_paths(ROOT)["intake"]
    controls = read_controls(ROOT)
    if controls.get("neural_link_enabled") is not True:
        _write_status(layout, {
            "schema": "axm.uc-openwaldo-local-loop/v1",
            "status": "PAUSED_NEURAL_LINK_OFF",
            "intake": str(intake),
            "model": model_name,
            "neural_link_start_sequence": controls.get("neural_link_start_sequence", 0),
        })
        return False
    minimum_sequence = int(controls.get("neural_link_start_sequence", 0))
    with _connection(layout["db"]) as connection:
        rows = _new_intake_rows(connection, intake, maximum, minimum_sequence)
        if not rows:
            _write_status(layout, {
                "schema": "axm.uc-openwaldo-local-loop/v1",
                "status": "IDLE_NO_NEW_EXPERIENCE",
                "intake": str(intake),
                "model": model_name,
                "neural_link_start_sequence": minimum_sequence,
            })
            return False

        batch_id = _batch_identity(rows)
        batch_path = _write_batch(layout, rows, batch_id)
        destination = f"axm/uc-experience/{batch_id[:20]}"
        print(f"UC experience batch: {len(rows)} records -> {destination}")

        if not _corpus_exists(waldo, env, destination):
            _run([
                str(waldo), "index", "ingest", str(batch_path), destination,
                "--title", f"AXM UC experience {batch_id[:12]}",
                "--license", "NOASSERTION",
                "--source", f"axm-local://uc-neural-experience/{batch_id}",
                "--source-category", "other",
                "--language", "und",
                "--force-format", "jsonl",
                "--text-column", "text",
            ], env=env)

        if not _model_exists(waldo, env, model_name):
            _run([str(waldo), "model", "init", model_name, "--preset", preset], env=env)

        before = inspect_model_state(layout["models"] / model_name)
        _run([
            str(waldo), "model", "train", model_name, destination,
            "--epochs", "1",
            "--batch-size", str(batch_size),
            "--learning-rate", str(learning_rate),
        ], env=env)
        after = inspect_model_state(layout["models"] / model_name)
        growth = write_growth_comparison(ROOT, before, after)
        if growth.get("status") != "REAL_NEURAL_GROWTH_OBSERVED":
            _write_status(layout, {
                "schema": "axm.uc-openwaldo-local-loop/v1",
                "status": "HOLD_TRAINING_RETURNED_WITHOUT_PROVEN_NEURAL_GROWTH",
                "batch_id": batch_id,
                "records": len(rows),
                "destination": destination,
                "model": model_name,
                "growth": growth,
            })
            raise ExperimentError("OpenWALDO training returned, but persistent non-simulated neural growth was not proven")

        trained_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        connection.executemany(
            "INSERT INTO consumed(event_id, batch_id, trained_at) VALUES (?, ?, ?)",
            [(str(row["axm"]["event_id"]), batch_id, trained_at) for row in rows],
        )
        connection.commit()
        _write_status(layout, {
            "schema": "axm.uc-openwaldo-local-loop/v1",
            "status": "REAL_NEURAL_GROWTH_OBSERVED",
            "batch_id": batch_id,
            "records": len(rows),
            "destination": destination,
            "model": model_name,
            "growth": growth,
        })
        print(f"Verified neural growth from {len(rows)} new UC experience records.")
        return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Feed new UC experience into a local real OpenWALDO learner.")
    parser.add_argument("--waldo", help="existing waldo binary; otherwise PATH/local build is used")
    parser.add_argument("--no-build", action="store_true", help="do not build WALDO with Go when no binary exists")
    parser.add_argument("--backend", default="auto", choices=("auto", "mlx", "pytorch", "torchtitan"), help="real backend only; fake is intentionally forbidden")
    parser.add_argument("--model", default="axm-uc-learner")
    parser.add_argument("--preset", default="10m")
    parser.add_argument("--max-records", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=0.0003)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args(argv)

    if args.max_records < 1 or args.batch_size < 1 or args.interval < 1:
        parser.error("--max-records, --batch-size and --interval must be positive")
    if not (0.0 < args.learning_rate <= 1.0):
        parser.error("--learning-rate must be in (0, 1]")

    state = neural_paths(ROOT)["base"]
    layout = _experiment_layout(state)
    try:
        waldo = _waldo_binary(args.waldo, state, build_if_missing=not args.no_build)
        env = _configure_waldo(waldo, layout, args.backend)
        while True:
            feed_once(
                waldo=waldo,
                env=env,
                layout=layout,
                model_name=args.model,
                preset=args.preset,
                maximum=args.max_records,
                batch_size=args.batch_size,
                learning_rate=args.learning_rate,
            )
            if not args.watch:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped by user.")
        return 130
    except ExperimentError as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
