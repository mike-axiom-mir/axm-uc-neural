#!/usr/bin/env python3
"""Run bounded real UC workflow-discovery practice and retain confirmed routes.

This is deterministic UC learning-by-use, not neural weight training. Each
profile searches installed typed operators, executes real candidate pipelines,
measures declared outcomes, repairs/reranks where possible, confirms repeatable
successes, and writes caller-owned workflow memory under the ordinary creations
workspace. This keeps generated evidence outside the live machine body.

Nothing is admitted to canonical UC automatically.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.atomic import atomic_write_json
from axm_uc.workflow_experiments import experiment
from axm_uc.workflow_memory import read_memory

BASE = ROOT / "creations" / "neural-experiment" / "workflow-practice"
PROFILE_NAMES = ("vent-hood", "character-motion", "code-project")


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _vent_hood() -> dict:
    request = _load("examples/workflows/vent-hood.json")["inputs"]["request"]
    # Keep a serious but bounded local practice pass. The canonical fixture has
    # enough alternatives to expose a failed source-UV route and a repaired bake.
    request["budget"]["trials"] = min(int(request["budget"].get("trials", 24)), 16)
    request["budget"]["rounds"] = min(int(request["budget"].get("rounds", 12)), 12)
    return request


def _character_motion() -> dict:
    recipe = _load("examples/character-motion/seedling-performance.json")["inputs"]["recipe"]
    return {
        "schema": "axm.workflow-experiment/v0.1",
        "intent": "Verify queried character motion geometry through installed UC operators.",
        "inputs": {
            "body": {"type": {"kind": "character-recipe"}, "values": [recipe]},
            "probe": {"type": {"kind": "motion-probe"}, "values": [
                {"clip": "walk", "times": [0, 0.37, 2.37]},
                {"clip": "walk", "times": [0, 0.5, 1.5, 2.5]},
            ]},
        },
        "goals": {
            "motion": {
                "type": {"kind": "motion-observation", "units": "m"},
                "checks": [{"metric": "maximum_target_error_m", "unit": "m", "max": 0.000001}],
            }
        },
        "objectives": [{
            "goal": "motion", "metric": "maximum_target_error_m", "unit": "m",
            "direction": "minimize", "target": 0, "scale": 0.001, "weight": 1,
        }],
        "budget": {"states": 2000, "plans": 24, "steps": 10, "trials": 6,
                   "rounds": 8, "batch_size": 3, "confirmation_cases": 1},
    }


def _code_project() -> dict:
    code = _load("examples/code/restock-project.json")["inputs"]["request"]
    return {
        "schema": "axm.workflow-experiment/v0.1",
        "intent": "Run declared inventory acceptance cases through installed UC code operators.",
        "inputs": {"program": {"type": {"kind": "code-request"}, "values": [code]}},
        "goals": {
            "code": {
                "type": {"kind": "code-project", "quality": "checked"},
                "checks": [
                    {"metric": "cases", "unit": "count", "min": 3},
                    {"metric": "languages", "unit": "count", "min": 2},
                ],
            }
        },
        "objectives": [
            {"goal": "code", "metric": "cases", "unit": "count",
             "direction": "maximize", "target": 3, "scale": 3, "weight": 1},
            {"goal": "code", "metric": "languages", "unit": "count",
             "direction": "maximize", "target": 2, "scale": 2, "weight": 1},
        ],
        "budget": {"states": 2000, "plans": 24, "steps": 10, "trials": 6,
                   "rounds": 8, "batch_size": 3, "confirmation_cases": 1},
    }


def requests() -> dict[str, dict]:
    return {
        "vent-hood": _vent_hood(),
        "character-motion": _character_motion(),
        "code-project": _code_project(),
    }


def _next_run(profile: str, base: Path) -> Path:
    folder = base / "runs" / profile
    folder.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(r"run-(\d{4})\Z")
    numbers = []
    for child in folder.iterdir():
        match = pattern.fullmatch(child.name)
        if child.is_dir() and match:
            numbers.append(int(match.group(1)))
    return folder / f"run-{(max(numbers, default=0) + 1):04d}"


def run_profile(profile: str, *, base: Path = BASE) -> dict:
    catalog = requests()
    if profile not in catalog:
        raise ValueError("unknown workflow-practice profile")
    memory = base / "memory" / profile
    output = _next_run(profile, base)
    result = experiment(ROOT, catalog[profile], str(output), memory=str(memory))
    retained = read_memory(ROOT, str(memory))
    summary = {
        "profile": profile,
        "status": result["status"],
        "run": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
        "report_sha256": result.get("report_sha256"),
        "trials": result.get("trials", 0),
        "confirmed": len(result.get("ranked", [])),
        "selected": result.get("selected"),
        "memory": {
            "confirmed_workflows": len(retained["workflows"]),
            "observations": retained["observations"],
            "stale": retained["stale"],
            "ignored": retained["ignored"],
        },
        "automatic_canon_admission": False,
        "truth": "Real bounded UC workflow experiments and reusable measured candidates; not global optimality or autonomous canon.",
    }
    atomic_write_json(output / "practice-summary.json", summary)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=(*PROFILE_NAMES, "all"), default="all")
    parser.add_argument("--base", type=Path, default=BASE)
    args = parser.parse_args(argv)
    selected = PROFILE_NAMES if args.profile == "all" else (args.profile,)
    rows = []
    for profile in selected:
        print(f"\n=== UC workflow practice: {profile} ===", flush=True)
        rows.append(run_profile(profile, base=args.base.resolve()))
        print(json.dumps(rows[-1], indent=2), flush=True)
    aggregate = {
        "schema": "axm.uc-workflow-practice-run/v1",
        "profiles": rows,
        "confirmed_workflows": sum(row["memory"]["confirmed_workflows"] for row in rows),
        "automatic_canon_admission": False,
    }
    print("\n" + json.dumps(aggregate, indent=2))
    return 0 if all(row["status"] in {"VERIFIED_WORKFLOWS", "HOLD_NO_CONFIRMED_WORKFLOW", "HOLD_CAPABILITY_GAP"} for row in rows) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        raise SystemExit(2)
