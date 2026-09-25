# Laptop preflight follow-up — 2026-09-25

Inspected runtime commit `20d4e0ee9322f666f0e4b6c19fa0d77177d7b8af` and
active wiring parent `156a17edf7dda4693b25955878d5030649c0f730`.

The [candidate-adoption CI job](https://github.com/mike-axiom-mir/axm-uc-neural/actions/runs/36169267958/job/108184538631)
completed `python tools/build.py` with `BUILD_OK`: 1,306 tests ran, five skipped.
The subsequent whitespace check failed with exit 128 because its hard-coded
donor commit `eb628500c952dcaeb31318983446265580b2466f` does not exist in this
repository's history. This was not a runtime test failure.

The workflow now checks the actual pull-request base / pre-push commit. Initial
pushes use Git's empty tree. The exact shell block was exercised locally in a
temporary Git repository: clean existing-base, zero-base and absent-base cases
passed; deliberate trailing whitespace failed. The real PR-base comparison
also passed locally. No test gate was removed.

Startup documentation now records that the pinned PyTorch resolver requires
Linux, Windows `.cmd` wrappers do not enter WSL, the UC creation loop is a
separate process, and the neural link begins at its explicit enable boundary.

This follow-up changes documentation and CI only. It does not claim a real
training run on Mike's laptop, installed WSL/backend dependencies, native
Windows training support, automatic checkpointing of the neural model, or
whole-experiment readiness.
