from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTROL_SCHEMA = "axm.uc-neural-experiment-controls/v1"
CONTROL_RELATIVE = Path("state") / "neural-experiment" / "controls.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _defaults() -> dict[str, Any]:
    return {
        "schema": CONTROL_SCHEMA,
        "uc_creative_enabled": False,
        "neural_link_enabled": False,
        "neural_link_start_sequence": 0,
        "preview_interval_seconds": 8,
        "updated_at": None,
    }


def control_path(root: Path | str) -> Path:
    return Path(root).resolve() / CONTROL_RELATIVE


def read_controls(root: Path | str) -> dict[str, Any]:
    path = control_path(root)
    if not path.is_file():
        return _defaults()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {**_defaults(), "control_state": "HOLD_INVALID_CONTROL_FILE"}
    if not isinstance(value, dict) or value.get("schema") != CONTROL_SCHEMA:
        return {**_defaults(), "control_state": "HOLD_INVALID_CONTROL_SCHEMA"}
    result = _defaults()
    if isinstance(value.get("uc_creative_enabled"), bool):
        result["uc_creative_enabled"] = value["uc_creative_enabled"]
    if isinstance(value.get("neural_link_enabled"), bool):
        result["neural_link_enabled"] = value["neural_link_enabled"]
    start = value.get("neural_link_start_sequence")
    if isinstance(start, int) and not isinstance(start, bool) and start >= 0:
        result["neural_link_start_sequence"] = start
    interval = value.get("preview_interval_seconds")
    if isinstance(interval, int) and not isinstance(interval, bool) and 3 <= interval <= 60:
        result["preview_interval_seconds"] = interval
    if isinstance(value.get("updated_at"), str):
        result["updated_at"] = value["updated_at"]
    return result


def _current_intake_sequence(root: Path | str) -> int:
    from .neural_experience_transport import paths, read_jsonl

    rows = read_jsonl(paths(root)["intake"])
    maximum = 0
    for row in rows:
        meta = row.get("axm") if isinstance(row.get("axm"), dict) else {}
        sequence = meta.get("sequence")
        if isinstance(sequence, int) and not isinstance(sequence, bool):
            maximum = max(maximum, sequence)
    return maximum


def _write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".controls-", suffix=".json", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def set_control(root: Path | str, name: str, value: Any) -> dict[str, Any]:
    if name not in {"uc_creative_enabled", "neural_link_enabled", "preview_interval_seconds"}:
        raise ValueError(f"unknown experiment control: {name}")
    controls = read_controls(root)
    controls.pop("control_state", None)

    if name in {"uc_creative_enabled", "neural_link_enabled"}:
        if not isinstance(value, bool):
            raise TypeError(f"{name} must be boolean")
        if name == "neural_link_enabled" and value and not controls["neural_link_enabled"]:
            # Enabling starts at the exact current boundary. Experience observed
            # while the link was off remains diagnostic evidence, not hidden
            # backlog training.
            controls["neural_link_start_sequence"] = _current_intake_sequence(root)
        controls[name] = value
    else:
        if isinstance(value, bool) or not isinstance(value, int) or not (3 <= value <= 60):
            raise ValueError("preview_interval_seconds must be an integer from 3 to 60")
        controls[name] = value

    controls["schema"] = CONTROL_SCHEMA
    controls["updated_at"] = _now()
    _write_atomic(control_path(root), controls)
    return controls


__all__ = ["CONTROL_SCHEMA", "CONTROL_RELATIVE", "control_path", "read_controls", "set_control"]
