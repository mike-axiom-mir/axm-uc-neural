from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .provenance_trace import build_trace, make_trace_id, source_context_from_payload

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
        "provenance": base / "provenance-trace.jsonl",
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
    experience_core = {
        "schema": EXPERIENCE_SCHEMA,
        "path_id": str(path_id),
        "event": str(event),
        "status": str(status),
        "payload": payload,
    }
    existing_events = read_jsonl(selected["events"])
    sequence = len(existing_events) + 1
    source_context = source_context_from_payload(payload)
    experience_core_sha256 = hashlib.sha256(canonical(experience_core).encode("utf-8")).hexdigest()
    trace_id = make_trace_id(
        sequence=sequence,
        experience_core_sha256=experience_core_sha256,
        source_context=source_context,
    )
    experience = {
        **experience_core,
        "trace_id": trace_id,
        "source_context": source_context,
    }
    text = canonical(experience)
    encoded = text.encode("utf-8")
    experience_sha256 = hashlib.sha256(encoded).hexdigest()
    event_id = hashlib.sha256(
        canonical({"experience_sha256": experience_sha256, "sequence": sequence}).encode("utf-8")
    ).hexdigest()
    received = len(encoded) <= MAX_RECORD_BYTES
    intake_status = "VERIFIED_NOOP_OVERSIZE"
    if received:
        append_jsonl(selected["intake"], {
            "text": text,
            "axm": {
                "schema": EXPERIENCE_SCHEMA,
                "event_id": event_id,
                "experience_sha256": experience_sha256,
                "sequence": sequence,
                "trace_id": trace_id,
                "source_kind": source_context.get("kind"),
                "source_actor": source_context.get("actor"),
                "path_id": str(path_id),
                "event": str(event),
            },
        })
        intake_status = "APPENDED"
    payload_sha256 = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
    append_jsonl(selected["events"], {
        "schema": "axm.uc-neural-coverage-event/v1",
        "event_id": event_id,
        "experience_sha256": experience_sha256,
        "sequence": sequence,
        "trace_id": trace_id,
        "source_kind": source_context.get("kind"),
        "source_actor": source_context.get("actor"),
        "path_id": str(path_id),
        "event": str(event),
        "status": str(status),
        "payload_sha256": payload_sha256,
        "intake_received": received,
        "intake_status": intake_status,
    })
    append_jsonl(
        selected["provenance"],
        build_trace(
            trace_id=trace_id,
            sequence=sequence,
            event_id=event_id,
            path_id=str(path_id),
            event=str(event),
            status=str(status),
            payload=payload,
            payload_sha256=payload_sha256,
            experience_sha256=experience_sha256,
            source_context=source_context,
            intake_received=received,
            intake_status=intake_status,
        ),
    )
    return refresh_uc_coverage(root)


def observe_uc_experience(root: Path | str, **kwargs: Any) -> dict[str, Any] | None:
    try:
        return record_uc_experience(root, **kwargs)
    except Exception:
        return None


def reset_experiment_diagnostics(root: Path | str) -> None:
    selected = paths(root)
    selected["base"].mkdir(parents=True, exist_ok=True)
    for name in ("events", "intake", "coverage", "coverage_report", "neural", "neural_report", "provenance"):
        selected[name].unlink(missing_ok=True)
