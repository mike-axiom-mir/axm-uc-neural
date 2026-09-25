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
    hashes = []
    errors = []
    for path in artifacts:
        try:
            if not path.resolve().is_relative_to(root):
                raise ValueError("artifact escapes model root")
            # Stream large models instead of loading another full copy into RAM.
            digest = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    size += len(chunk)
                    digest.update(chunk)
            hashes.append({"path": str(path.relative_to(root)), "bytes": size,
                           "sha256": digest.hexdigest()})
        except (OSError, ValueError) as exc:
            errors.append({"path": str(path.relative_to(root)), "error": str(exc)})
    by_path = {item["path"]: item for item in hashes}
    real_complete = 0
    simulated = 0
    verified_runs = []
    for path in runs:
        try:
            if not path.resolve().is_relative_to(root):
                raise ValueError("run receipt escapes model root")
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("run receipt must be an object")
            observation = value.get("observation")
            if not isinstance(observation, dict):
                continue
            simulated += int(observation.get("simulated") is True)
            # Missing/false-like values are not explicit evidence of a real run.
            if value.get("state") != "complete" or observation.get("simulated") is not False:
                continue
            real_complete += 1
            declared = observation.get("artifacts")
            if not isinstance(declared, list):
                continue
            verified = []
            for artifact in declared:
                if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
                    raise ValueError("invalid declared artifact")
                relative = Path(artifact["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("artifact path must stay inside its run")
                if relative.name != "model.safetensors":
                    continue
                candidate = path.parent / relative
                if not candidate.resolve().is_relative_to(path.parent.resolve()):
                    raise ValueError("artifact escapes its run")
                actual = by_path.get(str(candidate.relative_to(root)))
                if (actual is None or actual["bytes"] <= 0
                        or type(artifact.get("bytes")) is not int
                        or actual["bytes"] != artifact["bytes"]
                        or actual["sha256"] != artifact.get("sha256")):
                    raise ValueError("run artifact does not match its declared size and digest")
                verified.append(actual["sha256"])
            if verified:
                verified_runs.append({"run": str(path.relative_to(root)),
                                      "artifact_sha256": sorted(set(verified))})
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append({"path": str(path.relative_to(root)), "error": str(exc)})
    fingerprint = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "real_complete_runs": real_complete,
        "simulated_runs": simulated,
        "artifact_files": len(hashes),
        "artifact_bytes": sum(item["bytes"] for item in hashes),
        "artifact_fingerprint": fingerprint,
        "artifact_sha256": sorted({item["sha256"] for item in hashes}),
        "verified_runs": verified_runs,
        "evidence_errors": errors,
    }


def write_growth_comparison(machine_root: Path | str, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    selected = paths(machine_root)
    prior_runs = {item["run"] for item in before.get("verified_runs", [])}
    prior_content = set(before.get("artifact_sha256", []))
    changed_runs = [
        item["run"] for item in after.get("verified_runs", [])
        if item["run"] not in prior_runs
        and any(digest not in prior_content for digest in item["artifact_sha256"])
    ]
    # A new directory or an unrelated/simulated artifact is not a weight change.
    # Old aggregate-only observations cannot establish this stronger comparison.
    grew = (
        "artifact_sha256" in before and "verified_runs" in before
        and bool(changed_runs)
        and not before.get("evidence_errors") and not after.get("evidence_errors")
    )
    result = {
        "schema": "axm.openwaldo-growth-diagnostic/v1",
        "status": "REAL_NEURAL_GROWTH_OBSERVED" if grew else "REAL_NEURAL_GROWTH_NOT_PROVEN",
        "before": before,
        "after": after,
        "simulated_runs_count_as_growth": False,
        "changed_verified_runs": changed_runs,
        "proves_useful_learning": False,
    }
    selected["base"].mkdir(parents=True, exist_ok=True)
    selected["neural"].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    selected["neural_report"].write_text(
        "# OpenWALDO neural growth diagnostic\n\n"
        + f"Status: {result['status']}\n"
        + f"Real complete runs: {before['real_complete_runs']} -> {after['real_complete_runs']}\n"
        + f"Model artifacts: {before['artifact_files']} -> {after['artifact_files']}\n"
        + "Requires a new explicitly real completed run with verified, changed weight content.\n"
        + "Simulated backend runs never count as neural growth.\n"
        + "Weight changes do not prove useful learning.\n",
        encoding="utf-8",
    )
    return result
