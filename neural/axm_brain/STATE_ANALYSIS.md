# AXM neural state analysis

AXM Brain treats growth as something to inspect, not merely a benchmark score.

The state analyzer is a read-only microscope over the current neural state and
over differences between two verified brain snapshots. It does not change the
brain, choose rewards, or decide what should be learned.

## Five root directions

Experiences may be tagged with one or more top-level AXM directions:

- CREATE
- USE
- PLAY
- LEARN
- DISCOVER

These labels describe the direction of an experience. They do not create five
separate hidden personalities or imply that a weight belongs to one category.

The brain stores aggregate lifetime counts for these directions. It does not
need a permanent event-by-event activity log to answer how much experience it
has received in each direction.

## What the analyzer measures

A capture can report:

- host experience count;
- wake/sleep phase and cycle;
- supervised and reward update counts;
- sleep replay and pruning counts;
- CREATE / USE / PLAY / LEARN / DISCOVER exposure;
- replay buffer occupancy;
- parameter count and sparsity;
- matrix-level weight magnitude and norms;
- hidden/output state norms.

Comparing two snapshots reports:

- how many parameters changed;
- fraction of parameters changed;
- mean/max/L2 parameter drift;
- cosine similarity;
- sign flips;
- host-experience and sleep deltas;
- direction-exposure deltas.

This lets an experiment isolate, for example, what changed during wake use and
what changed during sleep consolidation.

## Truth boundary

Parameter movement is not itself understanding.

A larger norm, a sign flip, or a CREATE-tagged experience does not prove that
the brain learned a human-readable concept. Semantic claims need behavioral
probes or controlled causal interventions that demonstrate the claimed
relationship.

Future analyzers can add fixed probe suites, representation comparisons,
ablation/patching experiments, forgetting checks, and cross-task transfer
without changing this boundary.

The purpose is therefore not to make the neural state magically transparent.
It is to make AXM unusually measurable from birth, so later claims about growth
can be tied to evidence instead of benchmark mythology or stories.
