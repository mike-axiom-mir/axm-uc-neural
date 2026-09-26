#!/usr/bin/env python3
"""Direct neural learning from complete temporary UC simulation trajectories.

Every verified transition teaches immediately. Recurrent hidden state and
eligibility traces persist inside one trajectory and reset only between
independent simulations. The final terminal reward can therefore modulate traces
created by earlier steps.

High-throughput mode uses remember=False: raw simulation experiences are not
retained in neural replay memory. The durable checkpoint keeps the changed brain,
source identities, deterministic curriculum position and compact batch digests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from tools.run_uc_simulation_lab import prepare_dependencies, load_dependencies, source_identity


def providers():
    from axm_uc.trajectory_simulation import WorkflowTrajectorySimulation
    return {name: WorkflowTrajectorySimulation(name) for name in WorkflowTrajectorySimulation.FAMILIES}


def _reset_episode(brain):
    brain.hidden = [0.0] * brain.config.hidden_size
    brain.last_output = [0.0] * brain.config.output_size
    brain.trace_in = [[0.0] * brain.config.input_size for _ in range(brain.config.hidden_size)]
    brain.trace_rec = [[0.0] * brain.config.hidden_size for _ in range(brain.config.hidden_size)]
    brain.trace_out = [[0.0] * brain.config.hidden_size for _ in range(brain.config.output_size)]


def _digest_packet(packet):
    return json.dumps(packet, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _episode(brain, provider, seed, occurrence, *, train):
    from axm_neural_network.simulation_contract import verified_transition
    from neural.axm_brain import AXMBrain, Experience, XorShift64

    working = brain if train else AXMBrain.from_snapshot(brain.to_snapshot())
    actions_rng = XorShift64((seed ^ (occurrence * 104729) ^ 0x9D31) & XorShift64.MASK)
    actions = [actions_rng.uniform(-1.0, 1.0) for _ in range(provider.HORIZON)]
    if train:
        from axm_uc.neural_trajectory_bridge import learn_verified_trajectory
        receipt = learn_verified_trajectory(working, provider, seed, actions, remember=False)
        final = receipt["final_state"]
        return {
            "mse": receipt["mean_transition_mse"],
            "terminal_reward": receipt["terminal_reward"],
            "final_debt": sum(final[key] for key in ("structure", "surface", "detail", "verification")),
            "trace_sha256": receipt["trajectory_digest"],
        }
    _reset_episode(working)
    state = provider.reset(seed)
    transcript = hashlib.sha256()
    loss = 0.0
    terminal_reward = None
    for index, action in enumerate(actions):
        result = provider.step(state, action)
        event = verified_transition(provider, result["experience"], spec=provider.describe_space())
        if event["before"] != provider.snapshot(state)["body"]["state"]:
            raise ValueError("trajectory provider substituted the requested state")
        if event["terminal"] != (index + 1 == provider.HORIZON):
            raise ValueError("trajectory terminal boundary mismatch")
        prediction = working.predict(event["observation"], update_state=False)
        loss += sum((a - b) ** 2 for a, b in zip(prediction, event["target"])) / len(prediction)
        working.predict(event["observation"], update_state=True)
        transcript.update(_digest_packet(result["experience"]) + b"\n")
        terminal_reward = event.get("reward") if event["terminal"] else terminal_reward
        state = provider.restore(provider.snapshot(result["state"]))
    return {
        "mse": loss / provider.HORIZON,
        "terminal_reward": terminal_reward,
        "final_debt": state.structure + state.surface + state.detail + state.verification,
        "trace_sha256": transcript.hexdigest(),
    }


def _greedy_episode(brain, provider, seed):
    """Use learned transition predictions to choose each next temporary pass."""
    from axm_neural_network.simulation_contract import verified_transition
    from neural.axm_brain import AXMBrain

    working = AXMBrain.from_snapshot(brain.to_snapshot())
    _reset_episode(working)
    state = provider.reset(seed)
    total_mse = 0.0
    chosen = []
    terminal_reward = None
    for _ in range(provider.HORIZON):
        candidates = []
        for action in provider.ACTION_VALUES:
            observation = [state.structure, state.surface, state.detail, state.verification, action]
            prediction = working.predict(observation, update_state=False)
            bounded = [max(0.0, min(1.0, value)) for value in prediction]
            candidates.append((sum(bounded), action, prediction))
        _, action, predicted = min(candidates, key=lambda row: (row[0], row[1]))
        result = provider.step(state, action)
        event = verified_transition(provider, result["experience"], spec=provider.describe_space())
        total_mse += sum((a - b) ** 2 for a, b in zip(predicted, event["target"])) / len(predicted)
        # Preserve recurrent path context during evaluation, but do not learn.
        working.predict(event["observation"], update_state=True)
        state = provider.restore(provider.snapshot(result["state"]))
        chosen.append(action)
        if event["terminal"]:
            terminal_reward = event.get("reward")
    return {
        "terminal_reward": terminal_reward,
        "final_debt": state.structure + state.surface + state.detail + state.verification,
        "transition_mse": total_mse / provider.HORIZON,
        "actions": chosen,
    }


def evaluate(brain, provider_map, seeds):
    rows = {}
    total_reward = total_debt = total_mse = 0.0
    count = 0
    for name, provider in provider_map.items():
        rewards = debts = losses = 0.0
        for seed in seeds:
            outcome = _greedy_episode(brain, provider, seed)
            rewards += float(outcome["terminal_reward"])
            debts += outcome["final_debt"]
            losses += outcome["transition_mse"]
        n = len(seeds)
        rows[name] = {
            "greedy_mean_terminal_reward": rewards / n,
            "greedy_mean_final_debt": debts / n,
            "greedy_mean_transition_mse": losses / n,
            "episodes": n,
        }
        total_reward += rewards
        total_debt += debts
        total_mse += losses
        count += n
    return {
        "families": rows,
        "greedy_mean_terminal_reward": total_reward / count,
        "greedy_mean_final_debt": total_debt / count,
        "greedy_mean_transition_mse": total_mse / count,
        "episodes": count,
        "policy": "choose the pass with the lowest predicted next unresolved-work sum",
    }


def _atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def _fresh(seed=41):
    from neural.axm_brain import AXMBrain, BrainConfig
    # replay_capacity=0 is deliberate: high-throughput temporary simulations
    # change learned state without retaining raw experience bodies.
    return AXMBrain(BrainConfig(
        input_size=5,
        hidden_size=32,
        output_size=4,
        seed=seed,
        learning_rate=.025,
        reward_learning_rate=.004,
        eligibility_decay=.94,
        replay_capacity=0,
        sleep_replay_passes=0,
    ))


def train_batch(brain, provider_map, *, start_episode, episodes, training_seeds):
    families = list(provider_map)
    transcript = hashlib.sha256()
    rewards = 0.0
    losses = 0.0
    transitions = 0
    before = brain.to_snapshot()["sha256"]
    reward_updates_before = brain.reward_update_count
    experience_before = brain.host_experience_count
    started = time.perf_counter()
    for episode in range(start_episode, start_episode + episodes):
        family = families[episode % len(families)]
        occurrence = episode // len(families)
        seed = training_seeds[occurrence % len(training_seeds)]
        result = _episode(brain, provider_map[family], seed, occurrence, train=True)
        transcript.update(f"{episode}:{family}:{seed}:{result['trace_sha256']}\n".encode())
        rewards += float(result["terminal_reward"])
        losses += result["mse"]
        transitions += provider_map[family].HORIZON
    elapsed = time.perf_counter() - started
    if brain.host_experience_count - experience_before != transitions:
        raise ValueError("brain did not experience every trajectory transition")
    if brain.reward_update_count - reward_updates_before != episodes:
        raise ValueError("terminal reward was not applied exactly once per trajectory")
    if brain.replay:
        raise ValueError("temporary simulation experience leaked into replay memory")
    # Keep learned weights/counters/reward baseline, but do not persist the
    # transient hidden/eligibility state of the final temporary world.
    _reset_episode(brain)
    return {
        "episode_start": start_episode,
        "episode_end": start_episode + episodes,
        "episodes_added": episodes,
        "transitions_added": transitions,
        "brain_before": before,
        "brain_after": brain.to_snapshot()["sha256"],
        "trajectory_digest": transcript.hexdigest(),
        "mean_terminal_reward": rewards / episodes,
        "mean_transition_mse": losses / episodes,
        "wall_seconds": elapsed,
        "transitions_per_second": transitions / elapsed,
        "raw_experiences_retained": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    deps = ROOT / "state/neural-experiment/simulation/dependencies"
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--brain-root", type=Path, default=deps / "axm-neural-brain")
    parser.add_argument("--network-root", type=Path, default=deps / "axm-neural-network")
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "state/neural-experiment/simulation/trajectory-learning-v1.json")
    parser.add_argument("--episodes", type=int, default=512, help="additional complete 8-step trajectories")
    parser.add_argument("--brain-seed", type=int, default=41)
    args = parser.parse_args(argv)
    if not 1 <= args.episodes <= 100_000:
        parser.error("--episodes must be in [1, 100000]")
    if args.prepare:
        prepare_dependencies(deps)
    load_dependencies(args.brain_root.resolve(), args.network_root.resolve())

    from neural.axm_brain import AXMBrain
    from neural.axm_brain.state import snapshot_payload, verify_snapshot

    provider_map = providers()
    provider_specs = {name: provider.describe_space() for name, provider in provider_map.items()}
    training_seeds = tuple(range(256))
    evaluation_seeds = tuple(range(10_000, 10_032))

    if args.checkpoint.exists():
        saved = verify_snapshot(json.loads(args.checkpoint.read_text(encoding="utf-8")))
        if saved.get("schema") != "axm.uc-trajectory-learning/v1":
            raise ValueError("unsupported trajectory checkpoint")
        if saved.get("provider_specs") != provider_specs:
            raise ValueError("trajectory provider contract changed; preserve this checkpoint and start a new lineage")
        if saved.get("training_seeds") != list(training_seeds) or saved.get("evaluation_seeds") != list(evaluation_seeds):
            raise ValueError("trajectory curriculum changed; preserve this checkpoint and start a new lineage")
        brain = AXMBrain.from_snapshot(saved["brain"])
        if brain.config.replay_capacity != 0 or brain.replay:
            raise ValueError("trajectory checkpoint violates no-raw-replay contract")
        brain.wake()
        episode_count = saved["episode_count"]
        runs = list(saved["runs"])
        initial_evaluation = saved["initial_evaluation"]
    else:
        brain = _fresh(args.brain_seed)
        brain.wake()
        episode_count = 0
        runs = []
        initial_evaluation = evaluate(brain, provider_map, evaluation_seeds)

    before = evaluate(brain, provider_map, evaluation_seeds)
    run = train_batch(brain, provider_map, start_episode=episode_count,
                      episodes=args.episodes, training_seeds=training_seeds)
    after = evaluate(brain, provider_map, evaluation_seeds)

    body = {
        "schema": "axm.uc-trajectory-learning/v1",
        "brain": brain.to_snapshot(),
        "episode_count": episode_count + args.episodes,
        "trajectory_length": next(iter(provider_map.values())).HORIZON,
        "provider_specs": provider_specs,
        "training_seeds": list(training_seeds),
        "evaluation_seeds": list(evaluation_seeds),
        "initial_evaluation": initial_evaluation,
        "runs": runs + [{**run, "held_out_before": before, "held_out_after": after}],
        "sources": [source_identity(path) for path in (ROOT, args.brain_root.resolve(), args.network_root.resolve())],
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "storage_contract": {
            "raw_simulation_bodies_persisted": False,
            "neural_replay_capacity": brain.config.replay_capacity,
            "persistent_learning_state": "brain snapshot + compact deterministic run receipts",
        },
        "truth": [
            "Every verified temporary trajectory transition directly updates the experimental neural brain.",
            "Held-out behavior uses the learned transition model to choose the lowest-predicted-debt next pass; the brain is not yet a native action-policy network.",
            "Recurrent hidden state and eligibility traces persist inside a trajectory and reset between independent simulations.",
            "Only the terminal step carries the bounded final reward in this provider.",
            "The provider's design-debt dynamics and terminal reward are experimental heuristics, not aesthetic truth.",
            "This does not yet connect the general UC Creative Mode search loop to this stream.",
            "Millions of simulations are an architectural scaling direction, not a measured throughput claim from this Python experiment.",
        ],
        "automatic_adoption": False,
    }
    output = snapshot_payload(body)
    _atomic(args.checkpoint, output)
    durable = verify_snapshot(json.loads(args.checkpoint.read_text(encoding="utf-8")))
    restored = AXMBrain.from_snapshot(durable["brain"])
    if restored.to_snapshot() != brain.to_snapshot() or restored.replay:
        raise ValueError("durable trajectory learner did not restore exactly")
    print(json.dumps({
        "status": "SAVED",
        "checkpoint": str(args.checkpoint),
        "episodes_total": body["episode_count"],
        "transitions_total": restored.host_experience_count,
        "reward_updates_total": restored.reward_update_count,
        "replay_items": len(restored.replay),
        "run": run,
        "held_out_before": before,
        "held_out_after": after,
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        raise SystemExit(2)
