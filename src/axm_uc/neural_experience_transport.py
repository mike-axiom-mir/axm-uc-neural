from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

STATE_DIR = Path("state") / "neural-experiment"
EXPERIENCE_SCHEMA = "axm.uc-neural-experience/v1"
MAX_RECORD_BYTES = 8 * 1024 * 1024


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def paths(root: Path | str) -> dict[str, Path]:
    base = Path(root).resolve() / STATE_DIR
    return {
        "base": base,
        "events": base / "uc-wiring-events.jsonl",
        "intake": base / "openwaldo-intake.jsonl",
        "coverage": base / "uc-wiring-coverage.json",
        "coverage_report": base / "UC_WIRING_COVERAGE.md",
        "neural": base / "neural-growth.json",
        "neural_report": base / "NEURAL_GROWTH.md",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path} line {number} is not an object")
        result.append(value)
    return result


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")


def record_uc_experience(root: Path | str, *, path_id: str, event: str, payload: Any, status: str = "OBSERVED") -> dict[str, Any]:
    from .neural_coverage import refresh_uc_coverage

    selected = paths(root)
    experience = {
        "schema": EXPERIENCE_SCHEMA,
        "path_id": str(path_id),
        "event": str(event),
        "status": str(status),
        "payload": payload,
    }
    text = canonical(experience)
    event_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
    known = {
        str(row.get("axm", {}).get("event_id"))
        for row in read_jsonl(selected["intake"])
        if isinstance(row.get("axm"), dict)
    }
    received = len(text.encode("utf-8")) <= MAX_RECORD_BYTES
    intake_status = "VERIFIED_NOOP_OVERSIZE"
    if received and event_id in known:
        intake_status = "ALREADY_PRESENT"
    elif received:
        append_jsonl(selected["intake"], {
            "text": text,
            "axm": {
                "schema": EXPERIENCE_SCHEMA,
                "event_id": event_id,
                "path_id": str(path_id),
                "event": str(event),
            },
        })
        intake_status = "APPENDED"
    append_jsonl(selected["events"], {
        "schema": "axm.uc-neural-coverage-event/v1",
        "event_id": event_id,
        "path_id": str(path_id),
        "event": str(event),
        "status": str(status),
        "payload_sha256": hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest(),
        "intake_received": received,
        "intake_status": intake_status,
    })
    return refresh_uc_coverage(root)


def observe_uc_experience(root: Path | str, **kwargs: Any) -> dict[str, Any] | None:
    try:
        return record_uc_experience(root, **kwargs)
    except Exception:
        return None


def reset_experiment_diagnostics(root: Path | str) -> None:
    selected = paths(root)
    selected["base"].mkdir(parents=True, exist_ok=True)
    for name in ("events", "intake", "coverage", "coverage_report", "neural", "neural_report"):
        selected[name].unlink(missing_ok=True)
