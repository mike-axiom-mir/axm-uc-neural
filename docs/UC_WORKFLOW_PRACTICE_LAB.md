# UC workflow practice lab

This experiment uses UC's **existing real workflow-discovery machinery** to grow
reusable pipeline knowledge without changing canonical UC.

It is the primary pipeline-learning experiment for this branch. The separate
neural simulation lab is a secondary diagnostic about whether a learner can
predict small sequencing consequences.

## What it actually does

For every practice profile, UC:

1. reads the currently installed typed workflow operators;
2. searches bounded candidate compositions;
3. executes candidate pipelines against real UC capabilities;
4. measures the declared goal checks and objectives;
5. records actual failures and the first failing operator/check;
6. avoids repeating identical deterministic failure prefixes;
7. repairs/reranks by trying other compatible structures or input choices;
8. rebuilds successful cases for repeatability confirmation;
9. retains only **confirmed** reusable workflow structures in caller-owned memory.

A retained workflow is never a permanent PASS. On reuse it is rebound to current
inputs and operators and its current goals are executed again.

This is much closer to useful UC pipeline growth than teaching a neural model a
hand-written ordering rule.

## First practice profiles

The launcher currently exercises three different creation families:

- **vent-hood** — real 3D/material/UV/bake/preview routing. The existing fixture
  contains enough alternatives to expose an inadequate source-UV route and find
  a repaired measured route.
- **character-motion** — character recipe + motion-probe routing with measured
  target error.
- **code-project** — executable code-project routing with declared acceptance
  cases and language-count checks.

These are bounded starter profiles, not a claim that all 314+ Creative Hands are
already represented as typed workflow operators. Expanding operator coverage and
creative-domain practice is future experimental growth.

## Windows

Run:

```text
RUN_UC_WORKFLOW_PRACTICE.cmd
```

It runs all three profiles once. A later invocation creates new run directories
and reuses the existing measured workflow memory where contracts still fit.

Portable form:

```sh
python tools/run_uc_workflow_practice.py --profile all
python tools/run_uc_workflow_practice.py --profile vent-hood
python tools/run_uc_workflow_practice.py --profile character-motion
python tools/run_uc_workflow_practice.py --profile code-project
```

Node.js is required for installed operators that actually verify JavaScript or
otherwise depend on Node. Missing runtime capability remains a typed HOLD rather
than invented success.

## Where knowledge goes

All generated practice evidence lives under:

```text
creations/neural-experiment/workflow-practice/
  runs/
    vent-hood/
    character-motion/
    code-project/
  memory/
    vent-hood/
    character-motion/
    code-project/
```

This is intentionally an ordinary **creation workspace**, not `state/` and not
source code. UC's ordinary creation boundary forbids workflow experiments from
writing inside the live machine body.

Each memory collection can contain:

- exact workflow observations, including failures;
- confirmed repeatable observations;
- `axm.learned-workflow/v0.1` reusable structural templates.

The templates exclude concrete source choices. They preserve structure and
operator versions, then require fresh binding and fresh checks on every reuse.

## Relationship to the neural simulation lab

`RUN_UC_SIMULATION_LAB.cmd` now starts/resumes a separate
`session-workflow-v2.json` learner. It mixes:

- the existing three canvas-fit simulation families;
- four synthetic workflow-pass families grounded in current Product Workflow
  stage names.

The workflow-pass provider deliberately teaches only a bounded sequencing toy:
structure, surface, detail and verification debt. Its rules are experimental
heuristics. It is useful for testing direct learner persistence and route-choice
metrics, but **its learned weights are not the workflow knowledge proposed for
main UC**.

The useful candidate for main UC is the measured workflow memory above plus any
general orchestration improvements supported by its evidence.

## Relationship to Creative Mode and the 100 GB workspace

This launcher does **not** start the general Creative Mode heartbeat and does not
allocate a 100 GB creative workspace. It is a bounded pipeline-practice run.

The weekend cockpit currently launches the dashboard and WALDO feeder; it still
expects the actual UC creative/production loop to be started separately. The
dashboard's Creative toggle can pause/resume an attached Creative Practice
session, but the toggle by itself is not an overnight creator.

So tonight the experiment can be run as separate pieces:

- actual creative run — your normal UC Creative Mode / production loop;
- real workflow practice — `RUN_UC_WORKFLOW_PRACTICE.cmd`;
- neural sequencing diagnostic — `RUN_UC_SIMULATION_LAB.cmd`;
- dashboard + optional WALDO feeder — `START_WEEKEND_UC_NEURAL_LAB.cmd`.

Do not interpret one launcher as secretly enabling another.

## What would justify moving knowledge to main UC

Next week, inspect the generated workflow memory and run reports.

A good candidate for promotion is evidence such as:

- the same structural route confirmed across fresh current checks;
- a repaired pipeline consistently beating an inadequate route;
- useful operator combinations that recur across inputs;
- missing operator/contracts repeatedly blocking otherwise viable flows;
- detail or verification stages that measurably improve declared outcomes.

Do **not** copy an experimental neural checkpoint into main UC merely because its
loss decreased.

The intended transfer is:

```text
measured experiments
  -> inspect retained workflow structures + failures
  -> extract general pipeline knowledge
  -> implement/reuse that knowledge in main UC
  -> rerun main-UC verification
```

No automatic canon admission occurs anywhere in this lab.
