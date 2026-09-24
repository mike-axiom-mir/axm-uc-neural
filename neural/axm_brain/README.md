# AXM Direct Brain v0.1

A small AXM-native neural substrate for the **neural-under-software** experiment.

This is not a pretrained model and it is not a WALDO fork. It begins from a deterministic birth seed with newly initialized weights and changes through explicit experience supplied by its host software.

## What exists in v0.1

- recurrent hidden state;
- direct online learning from teaching targets;
- reward-modulated eligibility learning;
- bounded persistent replay memory;
- explicit `wake` and `sleep` states;
- sleep replay/consolidation and tiny-weight pruning;
- deterministic, serializable PRNG state;
- complete inspectable brain snapshots with SHA-256 integrity checking;
- no network, shell, tool, or autonomous filesystem authority inside the brain.

The host owns observations, actions, permissions, persistence locations, and what counts as useful feedback.

## State model

```text
birth(seed)
   |
   v
 WAKE -- experience --> neural change + bounded replay
   |                         |
   | sleep()                 |
   v                         |
 SLEEP -- replay/consolidate-+
   |
   | wake()
   v
 WAKE (next cycle)
```

The wake/sleep names are explicit computational phases, not claims about biology or consciousness.

## Minimal use

```python
from neural.axm_brain import AXMBrain, BrainConfig, Experience

brain = AXMBrain(
    BrainConfig(input_size=8, hidden_size=32, output_size=4, seed=1)
)

output = brain.experience(
    Experience(
        observation=[0.0] * 8,
        reward=1.0,
        source="uc",
        tag="successful-tool-path",
    )
)

brain.sleep()
snapshot = brain.to_snapshot()
brain = AXMBrain.from_snapshot(snapshot)
brain.wake()
```

## Truth boundary

v0.1 proves that the repository has an AXM-built persistent recurrent network that can change its own neural parameters from host-supplied experience and preserve that changed state across snapshots. It does **not** prove general intelligence, useful long-horizon learning, or superiority to WALDO. Those require experiments.

## Why this sits beside WALDO

`neural/waldo/` remains an independent baseline/fallback. `neural/axm_brain/` exists so UC can later run the same class of experiment against an AXM-controlled neural substrate without importing WALDO weights or learned state.
