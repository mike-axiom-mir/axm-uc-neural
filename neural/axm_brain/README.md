# AXM Direct Brain v0.2

A small AXM-native neural substrate for the **neural-under-software** experiment.

This is not a pretrained model and it is not a WALDO fork. It begins from a
deterministic birth seed with newly initialized weights and changes through
explicit experience supplied by its host software.

## What exists

- recurrent hidden state;
- direct online learning from teaching targets;
- reward-modulated eligibility learning;
- bounded persistent replay memory;
- explicit `wake` and `sleep` states;
- sleep replay/consolidation and tiny-weight pruning;
- deterministic, serializable PRNG state;
- complete inspectable brain snapshots with SHA-256 integrity checking;
- named software I/O contracts with their own SHA-256 fingerprint;
- persisted binding between learned state and the exact software signal
  contract it learned under;
- CREATE / USE / PLAY / LEARN / DISCOVER experience tagging for aggregate
  growth analysis;
- a read-only state analyzer for measured neural drift;
- the four AXM roots embedded as an inspectable contract in every brain
  snapshot;
- explicit Genesis admission for the pre-experience neural birth state;
- deterministic G0 identity `g0:<lineage>:<sha256>`;
- a deterministic Continuity Spine that preserves demonstrated behavior without
  freezing exact neural weights;
- explicit PRESERVE / SUPERSEDE / FORGET continuity decisions;
- no network, shell, tool, or autonomous filesystem authority inside the brain.

The host owns observations, actions, permissions, persistence locations, and
what counts as useful feedback.

## AXM roots

The roots carried by the brain are:

**Truth · Agency · Continuity · Wisdom Before Speed**

They are not a neural reward function, obedience system, hidden control
channel, or capability ceiling. They are explicit review criteria for deciding
whether a changed brain state has enough evidence to become the next canonical
state.

See `ROOTS_AND_CONTINUITY.md`.

## Genesis

Before lived neural learning begins, a deterministic initialized brain can be
validated and explicitly admitted as **Genesis / G0**.

```text
birth candidate
    |
validate exact roots + zero experience + configuration + provenance
    |
durable admission evidence
    |
G0
    |
WAKE / experience / SLEEP / growth
```

G0 is immutable lineage truth. It is not overwritten by later learning.
Corrections require a new lineage/version.

See `GENESIS.md`.

## State model

```text
G0
 |
 v
WAKE -- experience --> neural change + bounded replay
 |                         |
 | sleep()                 |
 v                         |
SLEEP -- replay/consolidate+
 |
 | wake()
 v
WAKE (next cycle)
 |
 +--> candidate snapshot
          |
    Continuity Spine
    + AXM root review
          |
     ACCEPT / HOLD
```

The wake/sleep names are explicit computational phases, not claims about
biology or consciousness.

## Software contract

The neural matrix should not have to understand UC internals. A host defines a
small named contract:

```python
from neural.axm_brain import BrainIOContract, Channel

contract = BrainIOContract(
    name="my-software-v1",
    inputs=(
        Channel("success", 0.0, 1.0),
        Channel("load", 0.0, 100.0),
    ),
    outputs=("reuse", "explore"),
)

brain = contract.new_brain(hidden_size=32, seed=1)
raw = brain.experience(
    {"success": 1.0, "load": 20.0},
    reward=1.0,
    directions=("USE", "LEARN"),
)
named_output = brain.output_state(raw)
```

The contract fingerprint travels with the bound snapshot. Changing channel
names, order, ranges, outputs, or the contract identity changes that
fingerprint.

## Truth boundary

v0.2 proves that the repository has an AXM-built persistent recurrent network
that can change neural parameters from host-supplied experience, preserve that
state across snapshots, expose measurable state growth, carry the AXM root
contract, admit a deterministic pre-experience G0, and check later candidate
states against deterministic continuity probes.

It does **not** prove general intelligence, semantic understanding, useful
long-horizon continual learning, or superiority to WALDO. Those require
experiments.

## Why this sits beside WALDO

`neural/waldo/` remains an independent baseline/fallback.
`neural/axm_brain/` exists so UC can later run the same class of experiment
against an AXM-controlled neural substrate without importing WALDO weights or
learned state.
