from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from typing import Iterable

from .analyzer import StateAnalyzer
from .core import AXMBrain
from .roots import AXM_ROOT_CONTRACT, RootReview


CONTINUITY_DISPOSITIONS = ("PRESERVE", "SUPERSEDE", "FORGET")


def _canonical_bytes(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class ContinuityProbe:
    probe_id: str
    observations: tuple[tuple[float, ...], ...]
    expected_outputs: tuple[tuple[float, ...], ...]
    tolerance: float = 0.05
    disposition: str = "PRESERVE"
    reason: str = ""
    source_snapshot_sha256: str = ""
    replacement_probe_id: str | None = None

    def __post_init__(self) -> None:
        if not self.probe_id or self.probe_id.strip() != self.probe_id:
            raise ValueError("probe_id must be non-empty and trimmed")
        disposition = str(self.disposition).strip().upper()
        if disposition not in CONTINUITY_DISPOSITIONS:
            raise ValueError(
                f"unknown continuity disposition {self.disposition!r}"
            )
        if not self.observations:
            raise ValueError("continuity probe needs at least one observation")
        if len(self.observations) != len(self.expected_outputs):
            raise ValueError(
                "continuity probe observations and outputs must have equal length"
            )
        if self.tolerance < 0.0:
            raise ValueError("continuity probe tolerance must be >= 0")
        if disposition in ("SUPERSEDE", "FORGET") and not self.reason.strip():
            raise ValueError(
                f"{disposition} requires an explicit reason"
            )
        if disposition == "SUPERSEDE" and not self.replacement_probe_id:
            raise ValueError("SUPERSEDE requires replacement_probe_id")
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(
            self,
            "observations",
            tuple(
                tuple(float(value) for value in row)
                for row in self.observations
            ),
        )
        object.__setattr__(
            self,
            "expected_outputs",
            tuple(
                tuple(float(value) for value in row)
                for row in self.expected_outputs
            ),
        )

    def to_dict(self) -> dict:
        return {
            "probe_id": self.probe_id,
            "observations": [list(row) for row in self.observations],
            "expected_outputs": [
                list(row) for row in self.expected_outputs
            ],
            "tolerance": self.tolerance,
            "disposition": self.disposition,
            "reason": self.reason,
            "source_snapshot_sha256": self.source_snapshot_sha256,
            "replacement_probe_id": self.replacement_probe_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContinuityProbe":
        return cls(
            probe_id=str(data["probe_id"]),
            observations=tuple(
                tuple(float(value) for value in row)
                for row in data["observations"]
            ),
            expected_outputs=tuple(
                tuple(float(value) for value in row)
                for row in data["expected_outputs"]
            ),
            tolerance=float(data.get("tolerance", 0.05)),
            disposition=str(data.get("disposition", "PRESERVE")),
            reason=str(data.get("reason", "")),
            source_snapshot_sha256=str(
                data.get("source_snapshot_sha256", "")
            ),
            replacement_probe_id=data.get("replacement_probe_id"),
        )


class ContinuitySpine:
    """Deterministic capability anchors beside a plastic neural brain.

    The spine never edits weights. It evaluates whether a candidate brain still
    demonstrates behavior that was explicitly anchored for preservation.
    """

    SCHEMA = "axm-continuity-spine/v0.1"

    def __init__(self, probes: Iterable[ContinuityProbe] = ()) -> None:
        self._probes: dict[str, ContinuityProbe] = {}
        for probe in probes:
            self.add(probe)

    @property
    def probes(self) -> tuple[ContinuityProbe, ...]:
        return tuple(self._probes[key] for key in sorted(self._probes))

    def add(self, probe: ContinuityProbe) -> None:
        if probe.probe_id in self._probes:
            raise ValueError(f"duplicate continuity probe: {probe.probe_id}")
        self._probes[probe.probe_id] = probe

    @classmethod
    def capture(
        cls,
        probe_id: str,
        brain_snapshot: dict,
        observations: Iterable[Iterable[float]],
        *,
        tolerance: float = 0.05,
        reason: str = "",
    ) -> ContinuityProbe:
        rows = tuple(
            tuple(float(value) for value in row)
            for row in observations
        )
        if not rows:
            raise ValueError("capture requires at least one observation")
        brain = AXMBrain.from_snapshot(brain_snapshot)
        cls._reset_probe_state(brain)
        outputs = []
        for row in rows:
            outputs.append(
                tuple(
                    brain.predict(
                        row,
                        update_state=True,
                    )
                )
            )
        return ContinuityProbe(
            probe_id=probe_id,
            observations=rows,
            expected_outputs=tuple(outputs),
            tolerance=tolerance,
            disposition="PRESERVE",
            reason=reason,
            source_snapshot_sha256=str(
                brain_snapshot.get("sha256", "")
            ),
        )

    @staticmethod
    def _reset_probe_state(brain: AXMBrain) -> None:
        brain.hidden = [0.0] * brain.config.hidden_size
        brain.last_output = [0.0] * brain.config.output_size
        brain.trace_in = [
            [0.0] * brain.config.input_size
            for _ in range(brain.config.hidden_size)
        ]
        brain.trace_rec = [
            [0.0] * brain.config.hidden_size
            for _ in range(brain.config.hidden_size)
        ]
        brain.trace_out = [
            [0.0] * brain.config.hidden_size
            for _ in range(brain.config.output_size)
        ]

    def set_disposition(
        self,
        probe_id: str,
        disposition: str,
        *,
        reason: str,
        replacement_probe_id: str | None = None,
    ) -> None:
        if probe_id not in self._probes:
            raise KeyError(probe_id)
        self._probes[probe_id] = replace(
            self._probes[probe_id],
            disposition=disposition,
            reason=reason,
            replacement_probe_id=replacement_probe_id,
        )

    def evaluate(self, candidate_snapshot: dict) -> dict:
        results = []
        preserve_passed = True
        for probe in self.probes:
            if probe.disposition != "PRESERVE":
                results.append(
                    {
                        "probe_id": probe.probe_id,
                        "disposition": probe.disposition,
                        "status": "NON_BLOCKING",
                        "reason": probe.reason,
                        "replacement_probe_id": probe.replacement_probe_id,
                    }
                )
                continue

            brain = AXMBrain.from_snapshot(candidate_snapshot)
            self._reset_probe_state(brain)
            max_error = 0.0
            step_results = []
            probe_ok = True
            for observation, expected in zip(
                probe.observations,
                probe.expected_outputs,
            ):
                actual = tuple(
                    brain.predict(
                        observation,
                        update_state=True,
                    )
                )
                if len(actual) != len(expected):
                    raise ValueError(
                        f"probe {probe.probe_id}: output shape changed"
                    )
                errors = [
                    abs(a - b)
                    for a, b in zip(actual, expected)
                ]
                step_error = max(errors, default=0.0)
                max_error = max(max_error, step_error)
                step_ok = step_error <= probe.tolerance
                probe_ok = probe_ok and step_ok
                step_results.append(
                    {
                        "max_abs_error": step_error,
                        "passed": step_ok,
                    }
                )
            preserve_passed = preserve_passed and probe_ok
            results.append(
                {
                    "probe_id": probe.probe_id,
                    "disposition": "PRESERVE",
                    "status": "PASS" if probe_ok else "REGRESSION",
                    "tolerance": probe.tolerance,
                    "max_abs_error": max_error,
                    "steps": step_results,
                    "source_snapshot_sha256": (
                        probe.source_snapshot_sha256
                    ),
                }
            )
        return {
            "schema": "axm-continuity-evaluation/v0.1",
            "passed": preserve_passed,
            "preserve_count": sum(
                1
                for probe in self.probes
                if probe.disposition == "PRESERVE"
            ),
            "results": results,
            "truth_boundary": (
                "probe-retention-is-behavioral-evidence-not-proof-of-"
                "identical-internal-representation"
            ),
        }

    def review_transition(
        self,
        before_snapshot: dict,
        candidate_snapshot: dict,
        root_review: RootReview,
    ) -> dict:
        continuity = self.evaluate(candidate_snapshot)
        state_delta = StateAnalyzer.compare_snapshots(
            before_snapshot,
            candidate_snapshot,
        )
        accepted = continuity["passed"] and root_review.passed
        return {
            "schema": "axm-neural-transition-review/v0.1",
            "decision": "ACCEPT" if accepted else "HOLD",
            "root_review": root_review.to_dict(),
            "continuity": continuity,
            "state_delta": state_delta,
            "truth_boundary": (
                "acceptance-preserves-explicit-anchors-and-root-evidence-"
                "without-freezing-neural-weights"
            ),
        }

    def to_snapshot(self) -> dict:
        body = {
            "schema": self.SCHEMA,
            "root_contract_sha256": AXM_ROOT_CONTRACT.fingerprint,
            "probes": [probe.to_dict() for probe in self.probes],
        }
        return {
            "body": body,
            "sha256": hashlib.sha256(
                _canonical_bytes(body)
            ).hexdigest(),
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "ContinuitySpine":
        if not isinstance(snapshot, dict):
            raise ValueError("continuity snapshot must be a dict")
        body = snapshot.get("body")
        digest = snapshot.get("sha256")
        if not isinstance(body, dict) or not isinstance(digest, str):
            raise ValueError(
                "continuity snapshot must contain body and sha256"
            )
        expected = hashlib.sha256(
            _canonical_bytes(body)
        ).hexdigest()
        if expected != digest:
            raise ValueError(
                "continuity spine snapshot integrity check failed"
            )
        if body.get("schema") != cls.SCHEMA:
            raise ValueError("unsupported continuity spine schema")
        if (
            body.get("root_contract_sha256")
            != AXM_ROOT_CONTRACT.fingerprint
        ):
            raise ValueError(
                "continuity spine root contract does not match AXM roots"
            )
        return cls(
            ContinuityProbe.from_dict(item)
            for item in body.get("probes", [])
        )
