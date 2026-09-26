# Expanded UC Creative Mode experiment

This experiment widens the reachable creation space used during the UC + neural
weekend work. It exists because the machine already contains many creation
capabilities, while the original Creative Practice heartbeat exercised only a
small raster-edit repertoire.

The expanded loop does **not** add a second hidden creator. It calls existing
`UniversalCreationMachine.create()` routes with seeded, inspectable requests and
retains ordinary creation outputs under `creations/`.

## Why this exists

The question is not only:

> Can UC make more assets?

It is:

> When UC has many composable capabilities, does repeated creative exploration
> start producing different classes of things and useful cross-capability
> combinations?

A narrow asset-only loop cannot test that.

## Initial reachable creation classes

A fresh session deliberately covers these nine families once before switching to
seeded repeated exploration:

1. **parametric-structure** — retained shape-recipe GLB construction;
2. **browser-game** — a complete local playable browser game;
3. **web-project** — interactive local software built from the session catalog;
4. **native-visual** — executable coded visual/WebGL runtime output;
5. **material-product** — complete Product Workflow material creation;
6. **textured-3d-product** — geometry + generated material + native UV/bake +
   inspection previews through Product Workflow;
7. **creative-flow-mesh** — several Creative Hands composed through one
   deterministic Creative Flow DAG;
8. **python-tool** — inspectable software generated from the session's prior
   creation-class history;
9. **compound-hub** — a new validated mixed-media software project that uses the
   prior catalog, physically copies a bounded sample of earlier GLB/PNG/WebP/WAV
   realizations into its own project body, links them from the local interface,
   and then passes that newly combined project through a second UC capability
   that packages it as a portable creation bundle.

After first coverage, compound creation receives extra scheduling weight so the
experiment does not collapse back into an asset-variant factory.

This is still a starter vocabulary. It does not imply every installed UC
capability has already been connected to this exploratory host.

## Persistence and reuse

State lives at:

```text
creations/neural-experiment/expanded-creative/state.json
```

Each run gets its own directory under:

```text
creations/neural-experiment/expanded-creative/runs/
```

The state keeps:

- deterministic seed;
- next run index;
- per-family counts;
- compact run receipts;
- a bounded catalog of successful outputs;
- accumulated output bytes.

The catalog becomes input to later software/compound creations. That means later
runs can explicitly incorporate knowledge of what this session has already made
instead of behaving like every heartbeat is the first heartbeat.

Binary reuse is restricted after path resolution to the ordinary `creations/`
tree. A tampered catalog cannot point the compound builder at an arbitrary host
file. The mixed-project copy is additionally bounded to a small sample so the
ordinary neural/provenance record remains below its intake boundary.

The catalog is operational exploration memory, not aesthetic approval or machine
canon.

## Provenance and neural observation

Every generated request carries:

```text
kind = autonomous_creative
actor = uc-expanded-creative
interface = tools/run_uc_expanded_creative.py
session_id
run_index
family
```

Because all work goes through the existing machine creation surface, ordinary UC
experience/provenance observation remains active. If the experimental neural
link is enabled, those UC events can be visible to the existing feeder according
to its normal boundary.

This is separate from the numeric direct-trajectory learner described in
[UC_TRAJECTORY_LEARNING.md]. Arbitrary games/websites/GLBs are not silently
pretended to have the same numeric simulation contract.

## 100 GB overnight launcher

On Windows:

```text
RUN_UC_EXPANDED_CREATIVE_100GB.cmd
```

The launcher:

- turns `uc_creative_enabled` on explicitly;
- starts the expanded loop;
- gives it up to **8 active hours**;
- uses **100,000,000,000 bytes** as the accumulated-output stop threshold;
- allows a large run count so time/storage, not an arbitrary tiny demo count,
  normally determines the experiment;
- follows the existing dashboard Creative toggle: OFF pauses creation without
  consuming active-time budget, ON resumes it;
- turns the Creative control back off when the process exits normally.

The stop threshold is checked between creation runs. One in-flight bounded UC
creation may cross the threshold by its own output size before the loop can stop;
individual capabilities retain their own output/resource bounds.

Pressing Ctrl+C preserves the current state and completed outputs. If the process
or machine dies after a run directory was created but before session state was
committed, restart recovery never overwrites that directory: a complete run
receipt is reconstructed into session state, while an incomplete run is marked
as interrupted, preserved, and the monotonic run counter advances.

Portable form:

```sh
python tools/run_uc_expanded_creative.py \
  --hours 8 \
  --max-bytes 100000000000 \
  --max-runs 100000
```

Add `--follow-control` if the dashboard toggle should pause/resume the process.

## What counts as success

This experiment does **not** score artistic beauty automatically.

Useful evidence includes:

- the loop genuinely crossing output classes;
- successful multi-capability products;
- later creations incorporating prior catalog entries;
- compound creation succeeding across more than one capability;
- repeated gaps/errors that expose missing orchestration;
- workflow-practice memory showing better measured pipeline structures;
- neural trajectory experiments improving held-out search behavior;
- interesting artifacts worth human inspection.

A folder full of bad creations is still evidence about the exploration policy.
A small number of surprising cross-capability creations may be more interesting
than maximum byte usage.

## Relationship to main UC

Everything here stays in the UC-neural experiment lane.

The exploratory host does not modify the canonical UC source body, auto-adopt
capabilities, or promote creations into canon.

If the experiment reveals useful general behavior, the intended next step is to
extract the evidenced orchestration/pipeline knowledge and implement it
deliberately in main UC next week.
