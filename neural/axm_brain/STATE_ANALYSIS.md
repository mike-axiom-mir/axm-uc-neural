# AXM neural state analysis

AXM Brain treats growth as something to inspect, not merely a benchmark score.

The state analyzer is a read-only microscope over the current neural state and
over differences between two verified brain snapshots. It does not change the
brain, choose rewards, or decide what should be learned.

## Five software directions

Experiences may be tagged with one or more top-level AXM software directions:

- CREATE
- USE
- PLAY
- LEARN
- DISCOVER

These are **not AXM roots**. They describe the direction of an experience so
later analysis can ask where growth came from.

The AXM roots are Truth, Agency, Continuity, and Wisdom Before Speed. See
`ROOTS_AND_CONTINUITY.md`.

The direction labels do not create five hidden personalities or imply that a
weight belongs to one category.

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

The Continuity Spine adds a separate behavioral view: whether explicit
previously demonstrated capabilities still work after those state changes.

## Truth boundary

Parameter movement is not itself understanding.

A larger norm, a sign flip, or a CREATE-tagged experience does not prove that
the brain learned a human-readable concept. Semantic claims need behavioral
probes or controlled causal interventions that demonstrate the claimed
relationship.

The purpose is not to make the neural state magically transparent. It is to
make AXM unusually measurable from birth, so later claims about growth can be
tied to evidence instead of benchmark mythology or stories.
