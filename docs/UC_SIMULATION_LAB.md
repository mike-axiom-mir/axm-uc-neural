# UC simulation learning lab

This explicit experiment lets an AXM learner predict how UC's existing
`fit-known-shapes-inside-canvas` rule corrects a proposed rectangle. UC executes
its real `axm_uc.simulation._fit_shape` implementation; its behavior is not
reimplemented as a neural rule. The three simulation families vary the inputs
(inside, overflow, mixed). They are not three different creation capabilities.

On Windows, run **RUN_UC_SIMULATION_LAB.cmd**. It requires Python 3.11+ and Git,
fetches pinned Brain/Network source into the experiment's local dependency
folder, and performs 768 one-transition lessons. Subsequent runs resume the
same saved learner and curriculum. No LLM, GPU, NumPy or WALDO backend is needed.
The lab stops at its saved 10,000-transition budget; this is a bounded trial.
Do not confuse this launcher with `START_WEEKEND_UC_NEURAL_LAB.cmd`, which still
owns the existing WALDO cockpit/feeder experiment.

Portable command:

```sh
python tools/run_uc_simulation_lab.py --prepare
python tools/run_uc_simulation_lab.py --resume
```

Use `--episodes 384` for a smaller call. `--checkpoint <new-path>` creates a
separate learner; an existing checkpoint cannot be overwritten without
`--resume`. `--policy random` or `--policy error_guided` selects a policy only
when creating a fresh session. Saved policy, seed and budget persist on resume.
For already checked-out repositories use `--brain-root` and `--network-root`.
Those explicit paths support development; their source hashes and dirty status
are recorded rather than falsely labeled as pinned clean code.

Checkpoint location: `state/neural-experiment/simulation/session.json`.
The complete file contains the parent and current learner, source identities,
provider parameters, seed split, scheduler state, linked episode history and
behavioral results. Each save uses a temporary file and atomic replacement,
then reads the actual saved bytes back and restores the learner. An exclusive
writer lock prevents two launched runs from overwriting each other's learning.
After a hard crash, a remaining `.lock` causes HOLD; confirm the old process has
stopped before deleting only that lock. Checkpoints remain local runtime data.
The session records completed episodes; a crash during a call can lose that
call's unsaved work, while preserving the last checkpoint.

The brain receives five numeric inputs (rectangle coordinates and dimensions,
plus a bounded shift) and predicts four corrected shape values. Raw human
prompt is null. Experience is labeled `deterministic_simulation`, with seed,
before/after state, action, exact UC source hash, selected rule and verification.
The core learns directly after each simulated transition. It resets transient
recurrent state between examples. It does not learn arbitrary natural-language
creation, drive live UC actions, or establish visual quality.

## First measured comparison

Three predetermined brain seeds (17, 41, 73), 768 training transitions each,
64 training seeds and 64 distinct held-out seeds per family. Every method gets
the same training-transition budget. Evaluation is separate and never changes
the curriculum. All nine runs restored exactly; every policy/brain-seed pair
improved its mean held-out prediction error over the initial learner.

| Policy | Mean held-out squared error after learning |
| --- | ---: |
| Fixed round robin | 0.00415584 |
| Seeded random | 0.00411418 |
| Moving-error guided | 0.00412318 |

Moving-error selection is a scheduling heuristic based on the learner's
prediction errors, not a trained neural meta-selector. It did not beat random
overall and lost to both controls on brain seed 73. Fixed remains the default.
These results are limited to one rectangle-fitting rule and these seed splits.
Full per-family results, timings and exact source hashes are preserved in
`verification/2026-09-25-simulation-bridge/curriculum-comparison.json`.

Reproduce with matching sibling checkouts:

```sh
python tools/benchmark_uc_simulation.py --output comparison.json
```

Add `--full-dir <path>` to retain every complete session checkpoint. The compact
committed comparison retains checkpoint/history hashes and the exact generation
contract. It does not claim millions of transitions or measured peak RAM/VRAM.

## Existing experiment boundaries

This separate, explicitly launched AXM session does not feed synthetic examples
into the operational WALDO intake, change WALDO's learning settings, turn on the
neural-learning link, or replace a canonical UC brain. Deterministic UC remains
usable without either neural dependency. The existing Windows WALMI/WALDO
runtime handoff in `CODEX_LOCAL_WALDO_HANDOFF.md` still requires inspection of
Mike's actual laptop route; cloud verification cannot establish that route.
