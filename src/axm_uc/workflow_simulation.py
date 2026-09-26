"""Replayable UC workflow-pass simulation for learning pipeline consequences.

This experiment does not execute creative hands or decide artistic quality. It
uses UC's existing product-workflow stage contracts as the grounded vocabulary
for four generic pass classes: structure, surface, detail and verification.

The learner predicts what one pass does to a bounded workflow-debt state. The
deterministic provider remains authoritative and replayable; learned predictions
stay experimental and do not mutate UC pipelines.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random

from . import product_workflow


def _packet(body):
    body = deepcopy(body)
    data = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return {"body": body, "sha256": hashlib.sha256(data).hexdigest()}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("finite numeric value required")
    return float(value)


@dataclass(frozen=True)
class WorkflowState:
    structure: float
    surface: float
    detail: float
    verification: float
    seed: int
    step: int
    family: str


class WorkflowPassSimulation:
    simulator_id = "axm.uc.workflow-pass"
    version = "1"
    backend = "python"
    experience_source = "deterministic_simulation"
    FAMILIES = ("static-3d", "animated-3d", "game", "image")
    ACTION_NAMES = ("structure", "surface", "detail", "verification")
    ACTION_VALUES = (-0.75, -0.25, 0.25, 0.75)

    _STRUCTURE = {
        "brief", "direction", "blockout", "geometry", "assembly", "playable-loop",
        "rules", "world", "composition", "implementation", "architecture", "interaction",
    }
    _SURFACE = {
        "surface-intent", "maps", "map-checks", "look-development", "uv-layout",
        "asset-production", "layers", "audio-feedback",
    }
    _DETAIL = {
        "mesh-baking", "lod-collision", "rig-deformation", "motion", "motion-inspection",
        "refinement", "source-design", "mix",
    }

    def __init__(self, family="static-3d"):
        if family not in self.FAMILIES:
            raise ValueError("unknown workflow family")
        self.family = family
        self.capability_sha256 = hashlib.sha256(Path(product_workflow.__file__).read_bytes()).hexdigest()
        profile = product_workflow.PROFILES[family]
        stage_ids = [stage["id"] for stage in profile["stages"]]
        self.stage_groups = {
            "structure": [stage for stage in stage_ids if stage in self._STRUCTURE],
            "surface": [stage for stage in stage_ids if stage in self._SURFACE],
            "detail": [stage for stage in stage_ids if stage in self._DETAIL],
            "verification": [
                stage for stage in stage_ids
                if any(token in stage for token in ("check", "inspection", "validation", "playtest", "verification", "delivery", "retained-practice"))
            ],
        }
        if any(not rows for rows in self.stage_groups.values()):
            raise ValueError("workflow profile does not ground all four pass classes")

    def describe_space(self):
        return {
            "schema": "axm.simulation-space/v1",
            "simulator_id": self.simulator_id,
            "version": self.version,
            "backend": self.backend,
            "experience_source": self.experience_source,
            "observation_size": 5,
            "target_size": 4,
            "horizon": 1,
            "action_bounds": [-1.0, 1.0],
            "parameters": {
                "family": self.family,
                "passes": list(self.ACTION_NAMES),
                "action_values": list(self.ACTION_VALUES),
                "stage_groups": deepcopy(self.stage_groups),
            },
            "capability": "axm_uc.product_workflow.PROFILES",
            "capability_source_sha256": self.capability_sha256,
        }

    def reset(self, seed):
        if type(seed) is not int:
            raise ValueError("integer seed required")
        rng = random.Random(seed ^ int(hashlib.sha256(self.family.encode()).hexdigest()[:8], 16))
        debts = [rng.uniform(0.08, 0.92) for _ in range(4)]
        if self.family == "static-3d":
            debts[1] = min(1.0, debts[1] + 0.15)
            debts[2] = min(1.0, debts[2] + 0.18)
        elif self.family == "animated-3d":
            debts[2] = min(1.0, debts[2] + 0.24)
            debts[3] = min(1.0, debts[3] + 0.12)
        elif self.family == "game":
            debts[0] = min(1.0, debts[0] + 0.18)
            debts[3] = min(1.0, debts[3] + 0.18)
        else:
            debts[1] = min(1.0, debts[1] + 0.24)
            debts[2] = min(1.0, debts[2] + 0.16)
        return WorkflowState(*debts, seed, 0, self.family)

    def _validate(self, state):
        if not isinstance(state, WorkflowState) or state.family != self.family or type(state.seed) is not int or type(state.step) is not int or state.step not in (0, 1):
            raise ValueError("invalid workflow simulation state")
        for key in self.ACTION_NAMES:
            value = _number(getattr(state, key))
            if not 0 <= value <= 1:
                raise ValueError("workflow debt outside bounds")

    def snapshot(self, state):
        self._validate(state)
        return _packet({"schema": "axm.uc.workflow-state/v1", "space": self.describe_space(), "state": asdict(state)})

    def restore(self, snapshot):
        if not isinstance(snapshot, dict) or _packet(snapshot["body"]) != snapshot:
            raise ValueError("workflow snapshot integrity mismatch")
        body = snapshot["body"]
        if body.get("schema") != "axm.uc.workflow-state/v1" or body.get("space") != self.describe_space():
            raise ValueError("workflow provider identity mismatch")
        state = WorkflowState(**body["state"])
        self._validate(state)
        return state

    @staticmethod
    def _action_index(action):
        value = _number(action)
        if not -1 <= value <= 1:
            raise ValueError("action outside bounds")
        if value < -0.5:
            return 0
        if value < 0:
            return 1
        if value < 0.5:
            return 2
        return 3

    @staticmethod
    def _clamp(value):
        return max(0.0, min(1.0, value))

    def _apply(self, state, action_index):
        structure, surface, detail, verification = (
            state.structure, state.surface, state.detail, state.verification
        )
        before = (structure, surface, detail, verification)
        if action_index == 0:
            structure *= 0.22
            # Structural changes late in a pipeline create bounded downstream rework.
            surface = self._clamp(surface + 0.12 * before[0])
            detail = self._clamp(detail + 0.10 * before[0])
            verification = self._clamp(verification + 0.08 * before[0])
        elif action_index == 1:
            if structure > 0.35:
                surface *= 0.90
                detail = self._clamp(detail + 0.08 * structure)
                verification = self._clamp(verification + 0.05)
            else:
                surface *= 0.28
                detail = self._clamp(max(detail, before[1] * 0.25))
                verification = self._clamp(verification + 0.04)
        elif action_index == 2:
            if max(structure, surface) > 0.35:
                detail *= 0.88
                verification = self._clamp(verification + 0.06)
            else:
                detail *= 0.25
                verification = self._clamp(verification + 0.03)
        else:
            unresolved = max(structure, surface, detail)
            if unresolved <= 0.35:
                verification *= 0.18
            else:
                # Inspection exposes unresolved upstream work instead of laundering it into PASS.
                verification = max(verification, unresolved)
        return tuple(self._clamp(value) for value in (structure, surface, detail, verification))

    def step(self, state, action):
        self._validate(state)
        if state.step != 0:
            raise ValueError("terminal state")
        action = _number(action)
        index = self._action_index(action)
        target = list(self._apply(state, index))
        after = WorkflowState(*target, state.seed, 1, self.family)
        before_vector = [state.structure, state.surface, state.detail, state.verification]
        chosen = self.ACTION_NAMES[index]
        prerequisites_ready = {
            "structure": True,
            "surface": state.structure <= 0.35,
            "detail": max(state.structure, state.surface) <= 0.35,
            "verification": max(state.structure, state.surface, state.detail) <= 0.35,
        }[chosen]
        body = {
            "schema": "axm.micro-experience/v1",
            "experience_source": self.experience_source,
            "simulator_id": self.simulator_id,
            "simulator_version": self.version,
            "backend": self.backend,
            "parameters": self.describe_space(),
            "seed": state.seed,
            "before": asdict(state),
            "action": action,
            "after": asdict(after),
            "observation": before_vector + [action],
            "target": target,
            "terminal": True,
            "raw_human_prompt": None,
            "interpreted_intent": f"Predict the effect of one grounded {self.family} workflow pass.",
            "selected_capabilities": deepcopy(self.stage_groups[chosen]),
            "workflow_pass": chosen,
            "workflow_profile": self.family,
            "prerequisites_ready": prerequisites_ready,
            "verification": {
                "bounded_debt": all(0 <= value <= 1 for value in target),
                "source_profile_present": self.family in product_workflow.PROFILES,
                "stage_group_nonempty": bool(self.stage_groups[chosen]),
            },
        }
        return {"state": after, "experience": _packet(body)}

    def step_many(self, states, actions):
        if not isinstance(states, (list, tuple)) or not states or len(states) != len(actions):
            raise ValueError("aligned nonempty batch required")
        return [self.step(state, action) for state, action in zip(states, actions)]

    def verify_transition(self, packet):
        if not isinstance(packet, dict) or _packet(packet["body"]) != packet:
            raise ValueError("workflow experience integrity mismatch")
        body = packet["body"]
        expected = self.step(WorkflowState(**body["before"]), body["action"])["experience"]
        if expected != packet:
            raise ValueError("workflow experience does not reproduce from UC workflow contract")
        return deepcopy(body)

    @staticmethod
    def debt_score(target):
        if not isinstance(target, (list, tuple)) or len(target) != 4:
            raise ValueError("four-value workflow target required")
        return sum(_number(value) for value in target)
