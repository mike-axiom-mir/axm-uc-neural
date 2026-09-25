from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .neural_experience_transport import paths


def inspect_model_state(model_root: Path | str) -> dict[str, Any]:
    root = Path(model_root).resolve()
    runs = sorted(root.rglob("RUN.json")) if root.exists() else []
    artifacts = sorted(root.rglob("model.safetensors")) if root.exists() else []
    real_complete = 0
    simulated = 0
    for path in runs:
        value = json.loads(path.read_text(encoding="utf-8"))
        observation = value.get("observation") if isinstance(value, dict) else None
        is_simulated = bool(observation.get("simulated")) if isinstance(observation, dict) else False
        simulated += int(is_simulated)
        real_complete += int(value.get("state") == "complete" and not is_simulated)
    hashes = []
    for path in artifacts:
        data = path.read_bytes()
        hashes.append({"path": str(path.relative_to(root)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "real_complete_runs": real_complete,
        "simulated_runs": simulated,
        "artifact_files": len(hashes),
        "artifact_bytes": sum(item["bytes"] for item in hashes),
        "artifact_fingerprint": fingerprint,
    }


def write_growth_comparison(machine_root: Path | str, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    selected = paths(machine_root)
    grew = (
        after["real_complete_runs"] > before["real_complete_runs"]
        and after["artifact_files"] > 0
        and after["artifact_fingerprint"] != before["artifact_fingerprint"]
    )
    result = {
        "schema": "axm.openwaldo-growth-diagnostic/v1",
        "status": "REAL_NEURAL_GROWTH_OBSERVED" if grew else "REAL_NEURAL_GROWTH_NOT_PROVEN",
        "before": before,
        "after": after,
        "simulated_runs_count_as_growth": False,
    }
    selected["base"].mkdir(parents=True, exist_ok=True)
    selected["neural"].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    selected["neural_report"].write_text(
        "# OpenWALDO neural growth diagnostic\n\n"
        + f"Status: {result['status']}\n"
        + f"Real complete runs: {before['real_complete_runs']} -> {after['real_complete_runs']}\n"
        + f"Model artifacts: {before['artifact_files']} -> {after['artifact_files']}\n"
        + "Simulated backend runs never count as neural growth.\n",
        encoding="utf-8",
    )
    return result
