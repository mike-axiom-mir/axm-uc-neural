# UC Simulation Experience Bridge

**Status: research architecture with a bounded implementation**

Implementation update: [UC simulation lab](../docs/UC_SIMULATION_LAB.md) now
exposes the existing canvas-fit rule to a persistent AXM learner, with source
labels, exact replay, fixed/random/error-guided scheduling, and unseen-seed
evaluation. This narrow implementation does not establish the broader claims
below. The error-guided heuristic did not beat random overall in the first
three-seed comparison.

This note defines how AXM Universal Creation can become a high-throughput **experience source** for a persistent neural learner without making UC itself dependent on the neural layer.

The central idea is simple:

```text
UC can already execute deterministic creation/workflow machinery
        ↓
vary the situation many times
        ↓
run bounded simulations
        ↓
turn outcomes into explicitly sourced experience
        ↓
feed experience to the neural brain
        ↓
later behavior changes
```

The useful shift is from "UC generates a dataset" to "UC can act as a machine-speed laboratory whose runs become direct experience for a persistent brain."

This repository owns the **bridge**, not the canonical neural innovation architecture. The general brain-level design belongs in `axm-neural-brain`.

## What counts as a UC micro-simulation

A simulation does not need to render a world.

For UC, a micro-simulation can be any bounded state transition or mini-environment that can be rerun under controlled variation, for example:

- route one intent through several capability combinations;
- vary parameters of an asset/workflow recipe;
- try alternate construction orderings;
- test resource or dependency constraints;
- run a small deterministic game/world state;
- compare two memory/routing decisions;
- test an organ/capability candidate against generated fixtures;
- execute one small procedural design problem repeatedly with different seeds.

The cheap cases matter because machine-scale learning depends more on **how many useful state transitions can be produced per unit of compute** than on whether each simulation looks visually impressive.

## Direct experience path

The bridge should preserve a closed causal chain:

```text
simulation definition
-> initial state
-> seed / variation parameters
-> learner observation
-> learner choice or candidate action
-> UC deterministic execution
-> outcome
-> verification
-> learning signal
-> neural update
-> next simulation selected from new learned state
```

That last step is important. The learner should eventually be able to choose the next simulation based on what it has already learned instead of consuming a permanently fixed batch.

## Experience-source truth

Simulation-generated experience must remain distinguishable from external experience.

A useful event should include at least:

```text
experience_source = deterministic_simulation | procedural_simulation | external_run | replay
simulation_id
simulation_version
seed
initial_state_ref
variation_parameters
raw_human_prompt            # nullable
interpreted_intent          # nullable
selected_capabilities
actions
result_refs
verification_results
learning_signal
checkpoint_before
checkpoint_after
runtime_environment
```

Do not silently relabel a synthetic success as evidence that the same behavior succeeded in a real user task.

## UC remains independently usable

The deterministic UC body remains useful even if the neural learner is absent, disabled, reset to Genesis, or performs badly.

That separation should stay explicit:

```text
UC capability fabric
        │
        ├── normal deterministic use
        │
        ├── simulation / procedural variation
        │
        └── verification
                ↓
        experience bridge
                ↓
        neural learner
```

The neural layer may later influence choices through explicit interfaces, but it is not allowed to become an invisible prerequisite for ordinary UC execution.

## Simulation families

Rather than hand-writing millions of unrelated fixtures, UC can define **families** of small simulations.

Example:

```text
base task:
construct a valid dependency graph

vary:
- graph size
- missing component
- conflicting dependency
- available tools
- resource limit
- order constraints
- noise / irrelevant options
```

A single family can then generate a large number of distinct experiences while preserving a known causal structure.

## Adaptive simulation selection

The first stage can simply sample seeds.

Later, the neural brain can request simulations based on its current state:

```text
"I repeatedly fail when two plausible routes conflict"
        ↓
request more conflict-routing simulations
        ↓
learn
        ↓
held-out test
```

The bridge should therefore support both:

- externally scheduled simulation batches;
- learner-requested simulation descriptors.

The request is not authority. UC still validates that the requested simulation exists within the supported contract and resource budget.

## Innovation experiments

The same UC simulation fabric can test neural candidates without changing live UC:

```text
known brain checkpoint
-> isolated neural descendant
-> UC simulation family
-> direct learning
-> held-out UC simulations
-> optional real/external UC runs
-> compare parent and descendant
-> preserve evidence
```

This lets AXM ask a more useful question than "did the candidate's immediate score improve?"

It can ask:

> Did this neural mechanism learn more effectively from experience, and did that learning transfer to unseen conditions?

## First concrete experiment

A small proof should be enough.

1. Choose one deterministic UC task family with cheap execution.
2. Save one Genesis checkpoint.
3. Generate a bounded training set procedurally from fixed seeds.
4. Train one learner through direct simulation experience.
5. Keep a control learner at Genesis or train it with a fixed/non-adaptive schedule.
6. Test both on unseen seeds.
7. Record behavior, compute cost, checkpoints, and exact simulation provenance.
8. Repeat from Genesis to check whether the result is reproducible enough to support a behavioral claim.

A later comparison can test:

- random simulation choice;
- fixed curriculum;
- learned simulation choice.

The interesting claim to earn is:

> With the same simulation budget, experience-guided simulation selection improves held-out behavior.

## Throughput must be measured

"Millions of simulations" is an architectural possibility, not a current performance claim.

For each simulator, record:

- state transitions / second;
- complete simulations / second;
- average steps per simulation;
- CPU/GPU/RAM use;
- learner update cost;
- storage cost;
- duplicate/uninformative run rate.

A tiny pure-state simulator may run extremely fast; a Blender render or full software build will not. They should not be counted as equivalent units.

## Relationship to Universal Creation

UC already has a useful property for this direction: it contains deterministic capability, verification, search, and procedural creation machinery that can expose **why** a result happened rather than only emit opaque outputs.

The bridge should exploit that structure without turning every UC action into training data by default.

Simulation experience should be explicit, source-labeled, bounded, and inspectable.

## Relationship to AXM Neural Brain

The persistent neural brain owns:

- learned state;
- checkpoints;
- neural innovation experiments;
- simulation-selection learning;
- long-term discovery memory.

UC-Neural owns:

- how UC exposes simulations;
- how UC results become neural experience;
- how source/provenance remains intact across that bridge.

This avoids creating two competing neural architectures.

## Evidence boundary

This note does not prove that UC currently produces useful neural learning, that high-throughput simulation is implemented, or that a learner can choose better simulations.

Those claims require controlled runs showing retained behavioral change attributable to explicitly sourced simulation experience.

Required Notice: Copyright 2026 Mike - Axiom/Mir.
