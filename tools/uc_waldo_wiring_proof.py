#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc import capabilities as capabilities_module
from axm_uc.capabilities import CapabilityError, CapabilityStore
from axm_uc.live_creation import run_live_creation
from axm_uc.machine import UniversalCreationMachine
from axm_uc import machine as machine_module
from axm_uc.neural_coverage import refresh_uc_coverage
from axm_uc.neural_experience import reset_experiment_diagnostics
from axm_uc.neural_growth import inspect_model_state, write_growth_comparison


def _proof_builtin(root: Path, inputs: dict) -> dict:
    if inputs.get("fail") is True:
        raise CapabilityError("intentional wiring-proof failure")
    return {"proof": "returned", "input_keys": sorted(inputs)}


def _exercise_capability_kinds(root: Path) -> None:
    store = CapabilityStore(root)
    entrypoint = "uc-neural-wiring-proof"
    prior = capabilities_module.BUILTINS.get(entrypoint)
    capabilities_module.BUILTINS[entrypoint] = _proof_builtin
    source = {
        "id": "AXM-PROOF-SOURCE",
        "handles": ["proof-source"],
        "input_contract": {"required": []},
        "implementation": {"kind": "DETERMINISTIC_SOURCE", "entrypoint": entrypoint},
    }
    provider = {
        "id": "AXM-PROOF-PROVIDER",
        "handles": ["proof-provider"],
        "input_contract": {"required": []},
        "implementation": {"kind": "LOCAL_PROVIDER_BOUNDARY", "entrypoint": entrypoint},
    }
    evidence = {
        "id": "AXM-PROOF-EVIDENCE",
        "handles": ["proof-evidence"],
        "input_contract": {"required": []},
        "implementation": {"kind": "EXTERNAL_EVIDENCE_BOUNDARY", "entrypoint": entrypoint},
    }
    alias = {
        "id": "AXM-PROOF-ALIAS",
        "handles": ["proof-alias"],
        "input_contract": {"required": []},
        "implementation": {"kind": "DETERMINISTIC_ALIAS", "delegate": source["id"]},
    }
    composite = {
        "id": "AXM-PROOF-COMPOSITE",
        "handles": ["proof-composite"],
        "input_contract": {"required": []},
        "implementation": {
            "kind": "DETERMINISTIC_COMPOSITE",
            "steps": [{"id": "source", "capability": source["id"], "inputs": {}}],
        },
    }
    original_by_id = store.by_id
    delegates = {source["id"]: source}
    store.by_id = lambda capability_id: delegates.get(capability_id) or original_by_id(capability_id)
    try:
        store.invoke(source, {"fixture": "source"})
        try:
            store.invoke(source, {"fail": True})
        except CapabilityError:
            pass
        else:
            raise AssertionError("intentional capability failure did not fail")
        store.invoke(provider, {"fixture": "provider"})
        store.invoke(evidence, {"fixture": "evidence"})
        store.invoke(alias, {"fixture": "alias"})
        store.invoke(composite, {"fixture": "composite"})
    finally:
        if prior is None:
            capabilities_module.BUILTINS.pop(entrypoint, None)
        else:
            capabilities_module.BUILTINS[entrypoint] = prior


def emit(root: Path, reset: bool) -> dict:
    if reset:
        reset_experiment_diagnostics(root)
    machine = UniversalCreationMachine(root)

    request = json.loads((root / "examples/requests/create_real_site.json").read_text(encoding="utf-8"))
    request["inputs"]["path"] = "creations/uc-waldo-wiring-proof-site"
    trial = machine.trial(request)
    if trial.get("passed") is not True:
        raise RuntimeError("representative UC creation trial did not pass")

    error = machine.create({"kind": "static-web-project", "inputs": {}})
    if error.get("type") != "CREATION_ERROR":
        raise RuntimeError("representative UC failure path did not return CREATION_ERROR")

    gap = machine.create({"kind": "__uc_waldo_wiring_proof_missing__", "inputs": {}})
    if gap.get("type") != "CAPABILITY_GAP":
        raise RuntimeError("representative UC gap path did not return CAPABILITY_GAP")

    machine.direct({"prompt": "create a small local static website with inspectable source"})

    live = run_live_creation(root, {
        "schema": "axm-live-creation/v0",
        "run_id": "uc-waldo-wiring-proof",
        "domain": "wiring-proof",
        "source": "creations/uc-waldo-wiring-proof-site",
        "max_iterations": 1,
        "execute": [],
        "observe": [{"id": "index-exists", "type": "file-exists", "path": "index.html"}],
        "repairs": [],
        "policy": {"replace_existing_run": True},
    })
    if live.get("status") != "COMPLETE":
        raise RuntimeError("representative live-creation path did not complete")

    _exercise_capability_kinds(root)

    original_test = machine_module.test_capability_candidate
    machine_module.test_capability_candidate = lambda _root, path: {
        "passed": True,
        "candidate": str(path),
        "fixture": "wiring-boundary-only",
    }
    try:
        machine.test_candidate(root / "synthetic-wiring-proof-candidate.json")
    finally:
        machine_module.test_capability_candidate = original_test

    original_adopt = machine._adopt_candidate_unobserved
    machine._adopt_candidate_unobserved = lambda path: {
        "adopted": True,
        "candidate": str(path),
        "fixture": "wiring-boundary-only",
        "live_machine_body_modified": False,
    }
    try:
        machine.adopt_candidate(root / "synthetic-wiring-proof-candidate.json")
    finally:
        machine._adopt_candidate_unobserved = original_adopt

    coverage = refresh_uc_coverage(root)
    if coverage.get("status") != "COMPLETE":
        raise RuntimeError("UC wiring coverage incomplete: " + ", ".join(coverage.get("missing", [])))
    return coverage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    emit_p = sub.add_parser("emit")
    emit_p.add_argument("--root", type=Path, default=ROOT)
    emit_p.add_argument("--reset", action="store_true")
    inspect_p = sub.add_parser("inspect-model")
    inspect_p.add_argument("--model-root", type=Path, required=True)
    compare_p = sub.add_parser("compare-model")
    compare_p.add_argument("--root", type=Path, default=ROOT)
    compare_p.add_argument("--model-root", type=Path, required=True)
    compare_p.add_argument("--before", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == "emit":
        result = emit(args.root.resolve(), args.reset)
    elif args.command == "inspect-model":
        result = inspect_model_state(args.model_root)
    else:
        before = json.loads(args.before.read_text(encoding="utf-8"))
        after = inspect_model_state(args.model_root)
        result = write_growth_comparison(args.root.resolve(), before, after)
        if result.get("status") != "REAL_NEURAL_GROWTH_OBSERVED":
            print(json.dumps(result, indent=2, sort_keys=True))
            return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
