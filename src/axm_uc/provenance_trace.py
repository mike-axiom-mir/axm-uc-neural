from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

SOURCE_SCHEMA = "axm.source-context/v1"
TRACE_SCHEMA = "axm.provenance-trace/v1"

_CURRENT_SOURCE: ContextVar[dict[str, Any] | None] = ContextVar("axm_current_source_context", default=None)

SOURCE_KINDS = {
    "human_prompt",
    "model_request",
    "autonomous_creative",
    "scheduled_event",
    "machine_event",
    "replay",
    "imported",
    "unattributed",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _bounded_text(value: Any, maximum: int) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    if not result:
        return None
    return result[:maximum]


def normalize_source_context(value: Any) -> dict[str, Any]:
    """Normalize caller attribution without inventing identity.

    Invalid or missing caller metadata never prevents the underlying UC
    experience from being recorded. Instead the source is explicitly
    unattributed and the reason is retained.
    """
    if value is None:
        return {
            "schema": SOURCE_SCHEMA,
            "kind": "unattributed",
            "attribution_status": "UNATTRIBUTED",
        }
    if not isinstance(value, dict):
        return {
            "schema": SOURCE_SCHEMA,
            "kind": "unattributed",
            "attribution_status": "HOLD_INVALID_SOURCE_CONTEXT",
            "raw_context_sha256": _digest(value),
        }

    kind = _bounded_text(value.get("kind"), 80)
    if kind not in SOURCE_KINDS:
        return {
            "schema": SOURCE_SCHEMA,
            "kind": "unattributed",
            "attribution_status": "HOLD_INVALID_SOURCE_KIND",
            "declared_kind": kind,
            "raw_context_sha256": _digest(value),
        }

    result: dict[str, Any] = {
        "schema": SOURCE_SCHEMA,
        "kind": kind,
        "attribution_status": "ATTRIBUTED" if kind != "unattributed" else "UNATTRIBUTED",
    }
    for field, maximum in (
        ("actor", 200),
        ("interface", 200),
        ("source_event_id", 300),
        ("parent_trace_id", 128),
        ("session_id", 200),
        ("note", 500),
    ):
        text = _bounded_text(value.get(field), maximum)
        if text is not None:
            result[field] = text

    # Context metadata is intentionally bounded and scalar-only. The originating
    # request/prompt remains in the ordinary UC request when present; provenance
    # does not duplicate an unbounded second copy.
    metadata = value.get("metadata")
    if isinstance(metadata, dict):
        compact: dict[str, str | int | float | bool | None] = {}
        for key in sorted(metadata)[:16]:
            name = _bounded_text(key, 80)
            item = metadata[key]
            if name is None or not isinstance(item, (str, int, float, bool, type(None))):
                continue
            if isinstance(item, str):
                item = item[:300]
            compact[name] = item
        if compact:
            result["metadata"] = compact
    return result



def _with_origin_request(source: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    result = dict(source)
    result["origin_request_sha256"] = _digest(request)
    for field in ("prompt", "direction", "purpose"):
        value = request.get(field)
        if isinstance(value, str) and value.strip():
            result[f"origin_{field}_sha256"] = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return result


@contextmanager
def source_scope(value: Any) -> Iterator[dict[str, Any] | None]:
    """Carry declared source attribution through nested deterministic calls."""
    if value is None:
        token = _CURRENT_SOURCE.set(_CURRENT_SOURCE.get())
        try:
            yield _CURRENT_SOURCE.get()
        finally:
            _CURRENT_SOURCE.reset(token)
        return
    normalized = normalize_source_context(value)
    token = _CURRENT_SOURCE.set(normalized)
    try:
        yield normalized
    finally:
        _CURRENT_SOURCE.reset(token)


def current_source_context() -> dict[str, Any] | None:
    value = _CURRENT_SOURCE.get()
    return dict(value) if isinstance(value, dict) else None

@contextmanager
def request_source_scope(request: Any) -> Iterator[dict[str, Any]]:
    """Bind one initiating request across all nested machine/capability activity."""
    if not isinstance(request, dict):
        normalized = normalize_source_context(None)
    else:
        normalized = _with_origin_request(
            normalize_source_context(request.get("axm_source")),
            request,
        )
    token = _CURRENT_SOURCE.set(normalized)
    try:
        yield normalized
    finally:
        _CURRENT_SOURCE.reset(token)


def source_context_from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return normalize_source_context(None)
    for key in ("request", "manifest"):
        value = payload.get(key)
        if isinstance(value, dict):
            explicit = normalize_source_context(value.get("axm_source"))
            return _with_origin_request(explicit, value)
    if "axm_source" in payload:
        return normalize_source_context(payload.get("axm_source"))
    inherited = current_source_context()
    if inherited is not None:
        return inherited
    return normalize_source_context(None)


def request_summary_from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"request_present": False}
    request = payload.get("request")
    if not isinstance(request, dict):
        request = payload.get("manifest")
    if not isinstance(request, dict):
        return {"request_present": False}

    prompt = request.get("prompt")
    direction = request.get("direction")
    purpose = request.get("purpose")
    result: dict[str, Any] = {
        "request_present": True,
        "request_sha256": _digest(request),
        "kind": _bounded_text(request.get("kind"), 160),
        "prompt_present": isinstance(prompt, str) and bool(prompt.strip()),
        "direction_present": isinstance(direction, str) and bool(direction.strip()),
        "purpose_present": isinstance(purpose, str) and bool(purpose.strip()),
    }
    if result["prompt_present"]:
        result["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if result["direction_present"]:
        result["direction_sha256"] = hashlib.sha256(direction.encode("utf-8")).hexdigest()
    if result["purpose_present"]:
        result["purpose_sha256"] = hashlib.sha256(purpose.encode("utf-8")).hexdigest()
    return result


def stage_for_path(path_id: str) -> str:
    if path_id == "machine.direct":
        return "interpretation"
    if path_id.startswith("capability."):
        return "execution"
    if path_id in {"machine.create", "machine.trial", "live_creation.run"}:
        return "execution"
    if path_id.startswith("candidate."):
        return "verification"
    return "machine_activity"


def make_trace_id(*, sequence: int, experience_core_sha256: str, source_context: dict[str, Any]) -> str:
    return hashlib.sha256(
        _canonical(
            {
                "schema": TRACE_SCHEMA,
                "sequence": sequence,
                "experience_core_sha256": experience_core_sha256,
                "source_context": source_context,
            }
        ).encode("utf-8")
    ).hexdigest()


def build_trace(
    *,
    trace_id: str,
    sequence: int,
    event_id: str,
    path_id: str,
    event: str,
    status: str,
    payload: Any,
    payload_sha256: str,
    experience_sha256: str,
    source_context: dict[str, Any],
    intake_received: bool,
    intake_status: str,
) -> dict[str, Any]:
    return {
        "schema": TRACE_SCHEMA,
        "trace_id": trace_id,
        "sequence": sequence,
        "source": source_context,
        "source_request": request_summary_from_payload(payload),
        "interpretation": {
            "stage": stage_for_path(path_id),
            "machine_path": path_id,
        },
        "execution": {
            "event": event,
            "status": status,
            "payload_sha256": payload_sha256,
        },
        "outcome": {
            "experience_event_id": event_id,
            "experience_sha256": experience_sha256,
        },
        "learning": {
            "intake_received": intake_received,
            "intake_status": intake_status,
            "same_trace_id_carried_to_intake": intake_received,
        },
        "truth": {
            "caller_identity_is_declared_not_inferred": True,
            "raw_prompt_is_not_duplicated_into_trace": True,
            "trace_does_not_grant_authority": True,
            "trace_does_not_claim_learning_usefulness": True,
        },
    }


__all__ = [
    "SOURCE_SCHEMA",
    "TRACE_SCHEMA",
    "SOURCE_KINDS",
    "normalize_source_context",
    "source_scope",
    "request_source_scope",
    "current_source_context",
    "source_context_from_payload",
    "request_summary_from_payload",
    "stage_for_path",
    "make_trace_id",
    "build_trace",
]
