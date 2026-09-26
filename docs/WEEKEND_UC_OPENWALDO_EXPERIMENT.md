> **Local Windows handoff:** before changing the learner runtime, read [CODEX_LOCAL_WALDO_HANDOFF.md](../CODEX_LOCAL_WALDO_HANDOFF.md). Mike already has a working WALMI/OpenWALDO path on this Windows laptop; inspect and reuse that proven route rather than inventing a second training stack.

# Weekend UC + OpenWALDO experiment

This branch is an experiment, not main.

## Start

Use the `codex/neural-growth-evidence-2026-09-25` branch for the wiring experiment
plus the growth-evidence repairs in PR #7. These changes are not yet on `main`.
Keep this experiment in its own checkout; do not replace an existing learned
WALMI/WALDO state directory with it.

### Training platform check

The nested WALDO source currently rejects native Windows in
`neural/waldo/internal/training/pytorch.go`. Its real training paths are Linux
(PyTorch/TorchTitan) and supported Apple Silicon macOS (MLX).
The `.cmd` files launch processes; they do **not** supply a Windows training
adapter or automatically enter WSL.

On a Windows laptop, verify the existing locally adapted WALDO installation
before reusing it, or run this experiment in a configured WSL/Linux environment.
Keep UC, the feeder and dashboard pointed at the same checkout/state directory.
Python 3.11+ is required for UC; building the nested CLI requires Go 1.25+ and
the real training backend requires its own dependencies. WSL installation alone
does not prove training works. No native-Windows training run has been verified
for this branch.

### Start the three processes

1. In the selected environment, start the cockpit with
   `python tools/uc_neural_dashboard.py --open-browser` (use `python3` if needed).
2. Start the feeder separately with
   `python tools/run_uc_openwaldo_local.py --watch --backend pytorch` on Linux/WSL,
   or select the verified backend for the actual host. Use `--waldo PATH` when
   deliberately selecting an existing compatible binary.
3. Enable **Neural learning link** before the UC actions you want it to learn
   from. Both dashboard controls initially default OFF; enabling the link starts
   at the current intake position and does not train earlier OFF-period events.
4. Start the actual UC creative/production loop in this checkout. The cockpit
   and feeder do not start that loop. Enable the creative control if using its
   attached creative-practice session. Every instrumented UC experience boundary
   writes to `state/neural-experiment/openwaldo-intake.jsonl`.
5. Run a small real batch before leaving it unattended. Confirm a completed
   non-simulated run, verified changed model content, and an advanced consumption
   ledger. A visible dashboard or growing intake count alone is insufficient.

The Windows wrappers remain convenient launchers only when their selected
runtime/binary has separately been verified for real training.

The feeder only consumes **new** experience occurrences. Repeated identical experiences remain separate occurrences and may therefore affect training frequency.

## What the feeder does

- uses an isolated WALDO config, index, lookaside, model store and SQLite consumption ledger under `state/neural-experiment/openwaldo-local/`;
- builds the nested OpenWALDO CLI with Go only when no `waldo` binary is already available;
- turns each bounded batch of new UC experience into a separate local OpenWALDO corpus;
- incrementally trains the same `axm-uc-learner` model, default preset `10m`, on that new batch only;
- refuses the OpenWALDO `fake` backend;
- advances the consumption ledger only after an explicitly non-simulated completed run has run-local `model.safetensors` content matching its recorded size/SHA-256 and differing from the previously observed content; copying identical weights into a new directory is not growth.

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

## Visual cockpit

The Windows entry surface is `START_WEEKEND_UC_NEURAL_LAB.cmd`; the training
platform requirements above still apply.

That launches:

- the local three-screen browser cockpit;
- the OpenWALDO feeder in a separate terminal.

The three screens stay separate:

1. **Neural brain** — feeder state, eligible/consumed experience and real-growth evidence.
2. **UC machine** — experience-path coverage, intake counts, creative-practice state and recent events.
3. **Current draft** — the exact current creative-practice PNG when an AXM creative-practice cartridge is attached; otherwise the newest existing UC preview image; otherwise an explicitly labelled activity map.

The dashboard never asks UC to make an extra render just for display. Preview refresh therefore does not create a parallel creative workload.

Both experiment toggles default OFF:

- **UC creative mode** is an explicit control flag and also pauses/resumes the latest attached AXM creative-practice session when the default cartridge exists at `state/neural-experiment/creative-practice.sqlite3`.
- **Neural learning link** starts a clean learning boundary at the current intake sequence when switched ON. Experience observed while it was OFF remains diagnostic evidence and is not secretly trained later.

The dashboard is loopback-only at `127.0.0.1:8765` and uses no external libraries or network services.
