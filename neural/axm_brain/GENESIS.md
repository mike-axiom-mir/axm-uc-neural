# AXM neural Genesis

Genesis is **the first state admitted into a lineage's canonical history**.

It is not necessarily the first causal event. Code loading, deterministic weight
initialization, dependency construction, and validation may happen before
Genesis. Those steps create a candidate. They do not become canonical lineage
history until admission succeeds.

The shared AXM state flow is:

```text
UNFORMED
   |
CONFIGURED
   |
INSTANTIATED
   |
CANDIDATE
   |
VALIDATED
   |
GENESIS (G0)
   |
ACTIVE
```

Explicit failure states are `REJECTED` and `COMMIT_FAILED`.

## Neural G0

For AXM Direct Brain, a Genesis candidate must still be a genuine neural birth
state:

- deterministic initialized weights are allowed;
- the exact PRNG state after initialization is bound;
- zero host experience;
- zero forward/lived steps;
- zero wake transitions;
- zero sleep cycles;
- zero replay history;
- zero supervised or reward updates;
- zero software-direction experience counters;
- zero transient recurrent/output state;
- zero eligibility traces.

This is the **Virgin Seed / birth state** before lived learning.

## Four roots are inside Genesis

Genesis binds the exact AXM root contract:

- Truth
- Agency
- Continuity
- Wisdom Before Speed

The root contract is part of the G0 identity, not a later preference.

Changing the root contract does not silently update the old Genesis. It creates
a different lineage/version.

The roots are still not a neural reward function, obedience mechanism, hidden
control channel, or intelligence ceiling.

## Genesis identity

A successful admission produces an identity of the form:

```text
g0:<lineage>:<sha256>
```

The digest binds:

- Genesis admission rule version;
- exact four-root contract and fingerprint;
- neural brain schema;
- complete brain snapshot hash;
- brain configuration hash;
- optional software/interface contract fingerprint;
- provenance;
- identities and roles;
- platform assumptions;
- randomness semantics;
- time semantics;
- validation results;
- admitting authority;
- durable commit evidence;
- the rule that post-Genesis correction requires a new lineage/version rather
  than silent replacement.

## Why this matters beyond neural software

The neural implementation is the first concrete use of the broader AXM Genesis
pattern.

The same pattern can later wrap:

- ordinary software bodies;
- AI bodies/stacks;
- robots and embodied controllers;
- simulation worlds;
- specialist machines.

What changes is the candidate validator. The invariant stays the same:

**construct → validate → durably admit G0 → transition from known ancestry.**

That gives later software, AI, and robotics a shared lineage language without
forcing them to share one runtime or one neural brain.

## Relationship to Continuity

Genesis is the immutable root of lineage.

The Continuity Spine governs later transitions:

```text
G0
 |
S1
 |
S2
 |
S3 ...
```

The brain may change radically between states. Continuity does not require
weight identity. It requires no silent loss of explicitly preserved behavior,
plus inspectable provenance for supersede/forget decisions.

## Truth boundary

A valid G0 proves that the admitted birth state satisfied the Genesis admission
checks and was bound to explicit commit evidence.

It does not prove that the neural architecture will learn well, become
intelligent, or remain useful. Those are empirical questions for the lineage
that grows from G0.
