from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from .roots import AXM_ROOT_CONTRACT, AXM_ROOTS
from .state import verify_snapshot
from .taxonomy import ROOT_DIRECTIONS


GENESIS_ADMISSION_SCHEMA = "axm.genesis-admission/v1"
GENESIS_FLOW = (
    "UNFORMED",
    "CONFIGURED",
    "INSTANTIATED",
    "CANDIDATE",
    "VALIDATED",
    "GENESIS",
    "ACTIVE",
)
GENESIS_FAILURE_STATES = ("REJECTED", "COMMIT_FAILED")


class GenesisAdmissionError(ValueError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _nonempty_text(value: Any, field: str) -> str:
    text = str(value).strip()
    if not text:
        raise GenesisAdmissionError(f"{field} must be non-empty")
    return text


def _zero_matrix(values: Any) -> bool:
    return all(
        float(item) == 0.0
        for row in values
        for item in row
    )


def _zero_vector(values: Any) -> bool:
    return all(float(item) == 0.0 for item in values)


@dataclass(frozen=True)
class GenesisValidation:
    schema: str
    passed: bool
    checks: tuple[tuple[str, bool, str], ...]

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "passed": self.passed,
            "checks": [
                {
                    "name": name,
                    "passed": passed,
                    "detail": detail,
                }
                for name, passed, detail in self.checks
            ],
        }

    @property
    def fingerprint(self) -> str:
        return _sha256(self.to_dict())


@dataclass(frozen=True)
class GenesisCandidate:
    """Pre-genesis candidate for one AXM neural lineage.

    Genesis is the first admitted canonical state, not the first causal event.
    Weight initialization may already have happened, but no lived experience,
    wake transition, sleep consolidation, or learning update may have occurred.
    """

    lineage: str
    brain_snapshot: dict
    provenance: Mapping[str, Any]
    identities_roles: Mapping[str, Any]
    platform_assumptions: Mapping[str, Any]
    interface_contract_sha256: str | None = None
    randomness_semantics: str = "deterministic-seed-and-prng-state-bound"
    time_semantics: str = "no-wall-clock-value-required-for-genesis-identity"
    rule_version: str = GENESIS_ADMISSION_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "lineage",
            _nonempty_text(self.lineage, "lineage"),
        )
        object.__setattr__(
            self,
            "randomness_semantics",
            _nonempty_text(
                self.randomness_semantics,
                "randomness_semantics",
            ),
        )
        object.__setattr__(
            self,
            "time_semantics",
            _nonempty_text(
                self.time_semantics,
                "time_semantics",
            ),
        )
        if self.rule_version != GENESIS_ADMISSION_SCHEMA:
            raise GenesisAdmissionError(
                "unsupported genesis admission rule version"
            )

    def validate(self) -> GenesisValidation:
        checks: list[tuple[str, bool, str]] = []

        try:
            body = verify_snapshot(self.brain_snapshot)
            snapshot_valid = True
            snapshot_detail = "brain snapshot integrity verified"
        except Exception as exc:
            body = {}
            snapshot_valid = False
            snapshot_detail = f"brain snapshot invalid: {exc}"
        checks.append(
            ("brain_snapshot_integrity", snapshot_valid, snapshot_detail)
        )

        if not snapshot_valid:
            return GenesisValidation(
                schema="axm.genesis-validation/v1",
                passed=False,
                checks=tuple(checks),
            )

        roots = body.get("roots")
        roots_exact = (
            isinstance(roots, dict)
            and roots.get("sha256") == AXM_ROOT_CONTRACT.fingerprint
            and roots.get("contract") == AXM_ROOT_CONTRACT.to_dict()
            and tuple(
                item.get("name")
                for item in roots.get("contract", {}).get("roots", [])
            )
            == AXM_ROOTS
        )
        checks.append(
            (
                "four_roots_exact",
                roots_exact,
                (
                    "Truth, Agency, Continuity, Wisdom Before Speed "
                    "match the canonical AXM root contract"
                    if roots_exact
                    else "brain does not carry the exact AXM root contract"
                ),
            )
        )

        state = body.get("state", {})
        virgin_checks = {
            "mode_wake": state.get("mode") == "wake",
            "zero_forward_steps": int(state.get("steps", -1)) == 0,
            "zero_wake_cycles": int(state.get("cycle", -1)) == 0,
            "zero_sleep_cycles": int(state.get("sleep_count", -1)) == 0,
            "zero_host_experience": int(
                state.get("host_experience_count", -1)
            )
            == 0,
            "zero_supervised_updates": int(
                state.get("supervised_update_count", -1)
            )
            == 0,
            "zero_reward_updates": int(
                state.get("reward_update_count", -1)
            )
            == 0,
            "zero_sleep_replay": int(
                state.get("sleep_replay_event_count", -1)
            )
            == 0,
            "zero_pruned_weights": int(
                state.get("total_pruned_weights", -1)
            )
            == 0,
            "empty_replay": state.get("replay") == [],
            "zero_hidden_state": _zero_vector(state.get("hidden", [1.0])),
            "zero_last_output": _zero_vector(
                state.get("last_output", [1.0])
            ),
            "zero_input_trace": _zero_matrix(
                state.get("trace_in", [[1.0]])
            ),
            "zero_recurrent_trace": _zero_matrix(
                state.get("trace_rec", [[1.0]])
            ),
            "zero_output_trace": _zero_matrix(
                state.get("trace_out", [[1.0]])
            ),
            "zero_untagged_experience": int(
                state.get("untagged_experience_count", -1)
            )
            == 0,
            "zero_direction_experience": all(
                int(
                    state.get(
                        "direction_experience_counts",
                        {},
                    ).get(direction, -1)
                )
                == 0
                for direction in ROOT_DIRECTIONS
            ),
        }
        virgin_passed = all(virgin_checks.values())
        failed_virgin = [
            name for name, passed in virgin_checks.items() if not passed
        ]
        checks.append(
            (
                "pre_experience_neural_birth",
                virgin_passed,
                (
                    "neural state is pre-experience and pre-sleep"
                    if virgin_passed
                    else "non-genesis neural activity detected: "
                    + ", ".join(failed_virgin)
                ),
            )
        )

        config = body.get("config")
        config_present = isinstance(config, dict) and bool(config)
        checks.append(
            (
                "configuration_bound",
                config_present,
                (
                    "brain configuration is present in the signed snapshot"
                    if config_present
                    else "brain configuration missing"
                ),
            )
        )

        provenance_present = bool(dict(self.provenance))
        checks.append(
            (
                "provenance_present",
                provenance_present,
                (
                    "genesis provenance supplied"
                    if provenance_present
                    else "genesis provenance is empty"
                ),
            )
        )

        identities_present = bool(dict(self.identities_roles))
        checks.append(
            (
                "identities_roles_present",
                identities_present,
                (
                    "genesis identities/roles supplied"
                    if identities_present
                    else "genesis identities/roles are empty"
                ),
            )
        )

        platform_present = bool(dict(self.platform_assumptions))
        checks.append(
            (
                "platform_assumptions_present",
                platform_present,
                (
                    "platform assumptions supplied"
                    if platform_present
                    else "platform assumptions are empty"
                ),
            )
        )

        return GenesisValidation(
            schema="axm.genesis-validation/v1",
            passed=all(passed for _, passed, _ in checks),
            checks=tuple(checks),
        )

    def manifest(
        self,
        validation: GenesisValidation,
        *,
        admitting_authority: str,
        commit_evidence: str,
    ) -> dict:
        return {
            "schema": GENESIS_ADMISSION_SCHEMA,
            "lineage": self.lineage,
            "roots": {
                "contract": AXM_ROOT_CONTRACT.to_dict(),
                "sha256": AXM_ROOT_CONTRACT.fingerprint,
            },
            "brain": {
                "schema": self.brain_snapshot["body"].get("schema"),
                "snapshot_sha256": self.brain_snapshot.get("sha256"),
                "config_sha256": _sha256(
                    self.brain_snapshot["body"].get("config", {})
                ),
            },
            "interface_contract_sha256": self.interface_contract_sha256,
            "provenance": dict(self.provenance),
            "identities_roles": dict(self.identities_roles),
            "platform_assumptions": dict(self.platform_assumptions),
            "randomness_semantics": self.randomness_semantics,
            "time_semantics": self.time_semantics,
            "validation": validation.to_dict(),
            "validation_sha256": validation.fingerprint,
            "admitting_authority": admitting_authority,
            "commit_evidence": commit_evidence,
            "post_genesis_rule": (
                "G0 is immutable; correction requires a new lineage/version "
                "rather than silent replacement"
            ),
        }


@dataclass(frozen=True)
class GenesisRecord:
    genesis_id: str
    manifest: dict
    manifest_sha256: str

    @property
    def lineage(self) -> str:
        return str(self.manifest["lineage"])

    def verify(self) -> None:
        expected = _sha256(self.manifest)
        if expected != self.manifest_sha256:
            raise GenesisAdmissionError(
                "genesis manifest integrity check failed"
            )
        expected_id = f"g0:{self.lineage}:{expected}"
        if self.genesis_id != expected_id:
            raise GenesisAdmissionError(
                "genesis identity does not match manifest"
            )
        roots = self.manifest.get("roots", {})
        if (
            roots.get("sha256") != AXM_ROOT_CONTRACT.fingerprint
            or roots.get("contract") != AXM_ROOT_CONTRACT.to_dict()
        ):
            raise GenesisAdmissionError(
                "genesis roots do not match canonical AXM roots"
            )

    def to_dict(self) -> dict:
        return {
            "genesis_id": self.genesis_id,
            "manifest_sha256": self.manifest_sha256,
            "manifest": self.manifest,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GenesisRecord":
        record = cls(
            genesis_id=str(data["genesis_id"]),
            manifest=dict(data["manifest"]),
            manifest_sha256=str(data["manifest_sha256"]),
        )
        record.verify()
        return record


class GenesisAdmission:
    """Explicit durable admission of a validated neural birth state as G0."""

    @staticmethod
    def admit(
        candidate: GenesisCandidate,
        *,
        admitting_authority: str,
        commit_evidence: str,
    ) -> GenesisRecord:
        authority = _nonempty_text(
            admitting_authority,
            "admitting_authority",
        )
        commit = _nonempty_text(
            commit_evidence,
            "commit_evidence",
        )
        validation = candidate.validate()
        if not validation.passed:
            failed = [
                check["name"]
                for check in validation.to_dict()["checks"]
                if not check["passed"]
            ]
            raise GenesisAdmissionError(
                "genesis candidate rejected: " + ", ".join(failed)
            )
        manifest = candidate.manifest(
            validation,
            admitting_authority=authority,
            commit_evidence=commit,
        )
        digest = _sha256(manifest)
        record = GenesisRecord(
            genesis_id=f"g0:{candidate.lineage}:{digest}",
            manifest=manifest,
            manifest_sha256=digest,
        )
        record.verify()
        return record
