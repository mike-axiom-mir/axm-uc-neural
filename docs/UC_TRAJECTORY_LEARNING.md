# UC direct trajectory learning lab

This experiment tests a stronger form of direct simulation learning than the
one-step simulation lab.

The question is:

> Can a fresh neural brain experience the **whole temporary search path** that UC
> takes toward an end result, learn at every intermediate transition, receive the
> final verified outcome as delayed reward, and keep the learning without keeping
> millions of temporary simulation bodies?

The current experimental answer is now **architecturally yes**, through an
explicit trajectory stream. It is not yet automatically attached to the general
UC Creative Mode search loop.

## Why this differs from end-result learning

End-result-only learning sees:

```text
start -> final design -> score
```

Trajectory learning sees:

```text
start
  -> temporary choice 1
  -> observed consequence
  -> temporary choice 2
  -> observed consequence
  -> ...
  -> final temporary result
  -> verification / terminal reward
```

Every verified transition calls the direct neural brain's `experience()` API.

Inside one trajectory:

- recurrent hidden state is preserved;
- reward eligibility traces are preserved;
- supervised next-state learning occurs at each transition;
- the final result supplies one bounded terminal reward.

Between independent simulated designs, hidden state and eligibility traces reset
so reward from one design cannot leak backward into another design.

This gives the final result a path to influence weights connected to earlier
steps through the brain's existing reward-modulated eligibility traces.

The current brain is primarily learning a **transition model**, not directly
emitting actions. Held-out evaluation therefore uses it model-based: at every
temporary step, the evaluator asks the learned brain to predict the next
unresolved-work state for each available pass and chooses the pass with the
lowest predicted debt. This turns learned consequence prediction into an
inspectable search policy without pretending the network already owns a native
action-policy head.

## No giant simulation archive

The high-throughput path creates the brain with:

```text
replay_capacity = 0
sleep_replay_passes = 0
```

and calls:

```text
brain.experience(..., remember=False)
```

Therefore temporary simulation experiences update learned state but do not enter
the brain's replay list.

The durable checkpoint keeps:

- the changed brain snapshot;
- exact provider contracts;
- training/evaluation seed sets;
- total completed trajectory count;
- source identities;
- compact per-run before/after brain hashes;
- a rolling digest of the temporary trajectory packets;
- aggregate loss/reward/throughput measurements.

It does **not** persist every simulated world or every transition packet.

Because the current curriculum and actions are deterministic from the recorded
seed/counter/provider/source contract, the class of experience can be reproduced
without keeping all temporary bodies.

## Current proof provider

The first provider is `WorkflowTrajectorySimulation`.

It runs an eight-step temporary workflow trajectory for four current UC product
families:

- static 3D;
- animated 3D;
- game;
- image.

Its state tracks bounded unresolved work in:

- structure;
- surface;
- detail;
- verification.

Each action chooses one of those passes. The terminal reward is bounded relative
debt reduction after eight steps.

**Important:** these debt dynamics and the reward are experimental heuristics.
They prove the trajectory-learning mechanism. They are not aesthetic truth and
are not the measured workflow knowledge proposed for main UC.

Real pipeline knowledge still comes from
[UC workflow practice lab](UC_WORKFLOW_PRACTICE_LAB.md), which executes actual
UC operator pipelines and measures their declared outcomes.

## Run it

Windows:

```text
RUN_UC_TRAJECTORY_LEARNING.cmd
```

Portable:

```sh
python tools/run_uc_trajectory_learning.py --prepare
```

Each invocation adds 512 complete eight-step trajectories by default and then
atomically saves:

```text
state/neural-experiment/simulation/trajectory-learning-v1.json
```

Run again to continue the same brain.

The checkpoint pins the simulator contract and curriculum. If those definitions
change, continuation HOLDS instead of silently teaching an old brain under new
simulation physics.

Use `--episodes N` for another bounded batch. The current CLI accepts at most
100,000 trajectories in one call. That bound is an experiment control, not a
claim that Python has measured million-simulation throughput.

## What this establishes

If verification passes, this experiment establishes that:

1. every intermediate simulation transition reaches the neural brain;
2. recurrent state can span an entire simulated search path;
3. the final terminal reward is applied once per completed trajectory;
4. eligibility traces can carry delayed reward across earlier trajectory steps;
5. raw simulation experiences do not need to remain in neural replay memory;
6. learned state survives checkpoint/restart;
7. held-out search can use the learned transition model to choose among temporary
   next steps and measure actual terminal reward/final debt;
8. the continuing brain can start with zero **experience** and acquire its state
   from explicitly sourced machine experience.

"Zero brain" here means **zero learned experience**, not zero numeric weights.
The current AXM brain starts from deterministic seeded random weights plus its
fixed architecture/root contract.

## What is not wired yet

The general Creative Mode / Free Creation loop does not yet automatically call
this trajectory stream for every temporary design search.

The final intended architecture would be:

```text
creative goal
  -> UC generates temporary candidate/search simulations
  -> every temporary transition streams directly to the neural learner
  -> final candidate is verified
  -> terminal outcome/reward closes the trajectory
  -> temporary simulation bodies are discarded
  -> changed neural state persists
  -> next search starts from the more experienced brain
```

That connection should be explicit and source-labelled. It should not turn every
ordinary UC action into training data by accident.

## Why this could scale strongly

If UC later exposes cheap, high-volume simulation families, learning volume is
no longer limited to one lesson per finished asset.

One finished design could contain thousands or millions of temporary causal
transitions. The learner could therefore receive far more direct experience than
the number of final products would suggest.

Whether that produces useful fast learning is an empirical question. Required
measurements include transfer to held-out simulations, final real-task results,
throughput, duplicate/uninformative transition rate, compute cost, and regression
against prior capabilities.

No million-simulation performance claim is made by this experiment.
