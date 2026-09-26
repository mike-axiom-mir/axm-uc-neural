"""Explicit bridge from a verified UC simulation trajectory to AXM neural experience.

Importing this module starts no learner and requires no neural dependency.
Neural/network modules are resolved only when learn_verified_trajectory() is
explicitly called by the experiment host.
"""
from __future__ import annotations

import hashlib
import json


def reset_trajectory_state(brain) -> None:
    """Reset transient episode context, not learned weights or counters."""
    brain.hidden = [0.0] * brain.config.hidden_size
    brain.last_output = [0.0] * brain.config.output_size
    brain.trace_in = [[0.0] * brain.config.input_size for _ in range(brain.config.hidden_size)]
    brain.trace_rec = [[0.0] * brain.config.hidden_size for _ in range(brain.config.hidden_size)]
    brain.trace_out = [[0.0] * brain.config.hidden_size for _ in range(brain.config.output_size)]


def learn_verified_trajectory(brain, provider, seed: int, actions, *, remember: bool = False) -> dict:
    """Teach one complete provider trajectory, preserving context inside it.

    The caller owns simulation selection and actions. The bridge verifies every
    transition against the provider contract before neural state changes.
    """
    from axm_neural_network.simulation_contract import describe, verified_transition
    from neural.axm_brain import Experience

    spec = describe(provider)
    actions = list(actions)
    if len(actions) != spec["horizon"]:
        raise ValueError("trajectory actions must match provider horizon")
    if type(seed) is not int:
        raise ValueError("trajectory seed must be an integer")
    if (brain.config.input_size, brain.config.output_size) != (spec["observation_size"], spec["target_size"]):
        raise ValueError("brain dimensions do not match simulation provider")
    brain.wake()
    reset_trajectory_state(brain)
    before_brain = brain.to_snapshot()["sha256"]
    state = provider.reset(seed)
    transcript = hashlib.sha256()
    total_loss = 0.0
    rewards = 0
    terminal_reward = None
    for index, action in enumerate(actions):
        result = provider.step(state, action)
        event = verified_transition(provider, result["experience"], spec=spec)
        if event["before"] != provider.snapshot(state)["body"]["state"]:
            raise ValueError("provider substituted trajectory state")
        if event["seed"] != seed or event["terminal"] != (index + 1 == spec["horizon"]):
            raise ValueError("trajectory seed or terminal boundary mismatch")
        prediction = brain.predict(event["observation"], update_state=False)
        total_loss += sum((a - b) ** 2 for a, b in zip(prediction, event["target"])) / len(prediction)
        reward = event.get("reward")
        if reward is not None:
            rewards += 1
            terminal_reward = reward
        brain.experience(
            Experience(
                event["observation"],
                target=event["target"],
                reward=reward,
                source=event["experience_source"],
                tag=result["experience"]["sha256"],
            ),
            remember=remember,
        )
        encoded = json.dumps(result["experience"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        transcript.update(encoded + b"\n")
        state = provider.restore(provider.snapshot(result["state"]))
    if rewards > 1:
        raise ValueError("trajectory emitted more than one reward event")
    return {
        "seed": seed,
        "transitions": spec["horizon"],
        "mean_transition_mse": total_loss / spec["horizon"],
        "terminal_reward": terminal_reward,
        "trajectory_digest": transcript.hexdigest(),
        "brain_before": before_brain,
        "brain_after": brain.to_snapshot()["sha256"],
        "final_state": provider.snapshot(state)["body"]["state"],
        "remembered_raw_experiences": spec["horizon"] if remember else 0,
    }


__all__ = ["learn_verified_trajectory", "reset_trajectory_state"]
