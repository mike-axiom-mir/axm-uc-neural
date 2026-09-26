"""Multi-step UC workflow trajectory simulation for direct neural experience.

This provider exists to test one specific architecture: the learner experiences
every temporary search step, keeps recurrent/eligibility state across the whole
trajectory, and receives a final bounded reward only at the terminal result.

The dynamics remain an explicit experimental heuristic. They are not aesthetic
truth and do not replace real workflow-discovery evidence.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math

from .workflow_simulation import WorkflowPassSimulation, WorkflowState


def _packet(body):
    value = deepcopy(body)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return {"body": value, "sha256": hashlib.sha256(encoded).hexdigest()}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("finite numeric value required")
    return float(value)


@dataclass(frozen=True)
class WorkflowTrajectoryState:
    structure: float
    surface: float
    detail: float
    verification: float
    initial_debt: float
    seed: int
    step: int
    family: str


class WorkflowTrajectorySimulation:
    simulator_id = "axm.uc.workflow-trajectory"
    version = "1"
    backend = "python"
    experience_source = "deterministic_simulation"
    FAMILIES = WorkflowPassSimulation.FAMILIES
    ACTION_NAMES = WorkflowPassSimulation.ACTION_NAMES
    ACTION_VALUES = WorkflowPassSimulation.ACTION_VALUES
    HORIZON = 8

    def __init__(self, family="static-3d"):
        self.pass_provider = WorkflowPassSimulation(family)
        self.family = family

    def describe_space(self):
        base = self.pass_provider.describe_space()
        return {
            "schema": "axm.simulation-space/v1",
            "simulator_id": self.simulator_id,
            "version": self.version,
            "backend": self.backend,
            "experience_source": self.experience_source,
            "observation_size": 5,
            "target_size": 4,
            "horizon": self.HORIZON,
            "action_bounds": [-1.0, 1.0],
            "parameters": {
                "family": self.family,
                "passes": list(self.ACTION_NAMES),
                "stage_groups": deepcopy(self.pass_provider.stage_groups),
                "terminal_reward": "bounded relative debt reduction; experimental heuristic",
            },
            "capability": "axm_uc.product_workflow.PROFILES",
            "capability_source_sha256": base["capability_source_sha256"],
        }

    def reset(self, seed):
        base = self.pass_provider.reset(seed)
        debt = base.structure + base.surface + base.detail + base.verification
        return WorkflowTrajectoryState(
            base.structure, base.surface, base.detail, base.verification,
            debt, seed, 0, self.family,
        )

    def _validate(self, state):
        if (not isinstance(state, WorkflowTrajectoryState) or state.family != self.family
                or type(state.seed) is not int or type(state.step) is not int
                or not 0 <= state.step <= self.HORIZON):
            raise ValueError("invalid workflow trajectory state")
        for key in ("structure", "surface", "detail", "verification"):
            value = _number(getattr(state, key))
            if not 0 <= value <= 1:
                raise ValueError("workflow trajectory debt outside bounds")
        if not 0 < _number(state.initial_debt) <= 4:
            raise ValueError("invalid initial workflow debt")

    def snapshot(self, state):
        self._validate(state)
        return _packet({"schema": "axm.uc.workflow-trajectory-state/v1",
                        "space": self.describe_space(), "state": asdict(state)})

    def restore(self, snapshot):
        if not isinstance(snapshot, dict) or _packet(snapshot["body"]) != snapshot:
            raise ValueError("workflow trajectory snapshot integrity mismatch")
        body = snapshot["body"]
        if body.get("schema") != "axm.uc.workflow-trajectory-state/v1" or body.get("space") != self.describe_space():
            raise ValueError("workflow trajectory provider identity mismatch")
        state = WorkflowTrajectoryState(**body["state"])
        self._validate(state)
        return state

    def step(self, state, action):
        self._validate(state)
        if state.step >= self.HORIZON:
            raise ValueError("terminal workflow trajectory")
        action = _number(action)
        index = self.pass_provider._action_index(action)
        temporary = WorkflowState(
            state.structure, state.surface, state.detail, state.verification,
            state.seed, 0, self.family,
        )
        target = list(self.pass_provider._apply(temporary, index))
        next_step = state.step + 1
        terminal = next_step == self.HORIZON
        after = WorkflowTrajectoryState(
            *target, state.initial_debt, state.seed, next_step, self.family,
        )
        final_debt = sum(target)
        reward = None
        if terminal:
            reward = max(-1.0, min(1.0, (state.initial_debt - final_debt) / state.initial_debt))
        chosen = self.ACTION_NAMES[index]
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
            "observation": [state.structure, state.surface, state.detail, state.verification, action],
            "target": target,
            "terminal": terminal,
            "reward": reward,
            "trajectory_step": state.step,
            "workflow_pass": chosen,
            "workflow_stages": deepcopy(self.pass_provider.stage_groups[chosen]),
            "selected_capabilities": [
                f"product-workflow:{self.family}:{stage}"
                for stage in self.pass_provider.stage_groups[chosen]
            ],
            "raw_human_prompt": None,
            "interpreted_intent": f"Experience one temporary {self.family} design-search trajectory.",
            "verification": {
                "bounded_debt": all(0 <= value <= 1 for value in target),
                "terminal_reward_only": reward is None if not terminal else reward is not None,
            },
        }
        return {"state": after, "experience": _packet(body)}

    def step_many(self, states, actions):
        if not isinstance(states, (list, tuple)) or not states or len(states) != len(actions):
            raise ValueError("aligned nonempty batch required")
        return [self.step(state, action) for state, action in zip(states, actions)]

    def verify_transition(self, packet):
        if not isinstance(packet, dict) or _packet(packet["body"]) != packet:
            raise ValueError("workflow trajectory experience integrity mismatch")
        body = packet["body"]
        expected = self.step(WorkflowTrajectoryState(**body["before"]), body["action"])["experience"]
        if expected != packet:
            raise ValueError("workflow trajectory experience does not reproduce")
        return deepcopy(body)
