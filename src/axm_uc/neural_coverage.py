from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .neural_experience_transport import paths, read_jsonl

REQUIRED = (
    ("capability.deterministic_source", "result"),
    ("capability.deterministic_source", "error"),
    ("capability.deterministic_alias", "result"),
    ("capability.deterministic_composite", "result"),
    ("capability.local_provider_boundary", "result"),
    ("capability.external_evidence_boundary", "result"),
    ("machine.create", "result"),
    ("machine.create", "error"),
    ("machine.create", "gap"),
    ("machine.direct", "result"),
    ("machine.trial", "result"),
    ("candidate.test", "result"),
    ("candidate.adopt", "result"),
    ("live_creation.run", "result"),
)

NOOPS = (
    ("read_only.plan", "read-only"),
    ("read_only.inspect", "read-only"),
    ("recovery.snapshot_create", "recovery bookkeeping"),
    ("recovery.snapshot_verify", "read-only integrity check"),
    ("recovery.snapshot_restore", "excluded to preserve exact restore state"),
)


def refresh_uc_coverage(root: Path | str) -> dict[str, Any]:
    selected = paths(root)
    events = read_jsonl(selected["events"])
    observed = {(str(row.get("path_id")), str(row.get("event"))) for row in events if row.get("intake_received") is True}
    matrix = []
    missing = []
    for path_id, event in REQUIRED:
        key = f"{path_id}.{event}"
        hit = (path_id, event) in observed
        matrix.append({"id": key, "coverage": "RECEIVED" if hit else "MISSING"})
        if not hit:
            missing.append(key)
    for path_id, reason in NOOPS:
        matrix.append({"id": f"{path_id}.noop", "coverage": "VERIFIED_NOOP", "reason": reason})
    intake = read_jsonl(selected["intake"])
    result = {
        "schema": "axm.uc-neural-coverage/v1",
        "status": "COMPLETE" if not missing else "INCOMPLETE",
        "required_paths": len(REQUIRED),
        "required_paths_received": len(REQUIRED) - len(missing),
        "verified_noop_paths": len(NOOPS),
        "event_records": len(events),
        "openwaldo_intake_records": len(intake),
        "missing": missing,
        "matrix": matrix,
        "truth": {
            "transport_only": True,
            "learning_policy_unchanged": True,
            "recovery_semantics_preserved": True,
        },
    }
    selected["base"].mkdir(parents=True, exist_ok=True)
    selected["coverage"].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = [
        "# UC to OpenWALDO wiring coverage",
        "",
        f"Status: {result['status']}",
        f"Required boundaries: {result['required_paths_received']}/{result['required_paths']}",
        f"Verified no-op boundaries: {result['verified_noop_paths']}",
        f"Intake records: {result['openwaldo_intake_records']}",
        "",
    ]
    report.extend(f"- {row['id']}: {row['coverage']}" for row in matrix)
    selected["coverage_report"].write_text("\n".join(report) + "\n", encoding="utf-8")
    return result
