# Weekend UC + OpenWALDO experiment

This branch is an experiment, not main.

## Start

1. Run UC normally in this checkout. Every instrumented UC production/experience boundary writes to `state/neural-experiment/openwaldo-intake.jsonl`.
2. On Windows, double-click `START_UC_OPENWALDO_EXPERIMENT.cmd`.
3. Leave that window open while UC produces work.

The feeder only consumes **new** experience occurrences. Repeated identical experiences remain separate occurrences and may therefore affect training frequency.

## What the feeder does

- uses an isolated WALDO config, index, lookaside, model store and SQLite consumption ledger under `state/neural-experiment/openwaldo-local/`;
- builds the nested OpenWALDO CLI with Go only when no `waldo` binary is already available;
- turns each bounded batch of new UC experience into a separate local OpenWALDO corpus;
- incrementally trains the same `axm-uc-learner` model, default preset `10m`, on that new batch only;
- refuses the OpenWALDO `fake` backend;
- advances the consumption ledger only after a non-simulated completed run plus a changed persisted `model.safetensors` fingerprint proves real neural-state growth.

## Diagnostics

UC wiring:
- `state/neural-experiment/uc-wiring-events.jsonl`
- `state/neural-experiment/uc-wiring-coverage.json`
- `state/neural-experiment/UC_WIRING_COVERAGE.md`

OpenWALDO growth:
- `state/neural-experiment/neural-growth.json`
- `state/neural-experiment/NEURAL_GROWTH.md`

Live feeder:
- `state/neural-experiment/openwaldo-local/STATUS.json`
- `state/neural-experiment/openwaldo-local/feed.sqlite3`

## Truth boundary

A received UC event is transport evidence, not learning evidence. A successful real OpenWALDO training run is still only evidence of parameter/state change from the supplied UC experience, not evidence that the change is useful. Usefulness is the weekend experiment.
