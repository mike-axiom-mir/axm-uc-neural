# AXM UC / Neural Experiment

This repository is the clean baseline for the experiment:

```
AXM Universal Creation
└── neural/
    └── waldo/
```

## Layer boundary

- **Upper layer — UC:** an exact tracked-file snapshot of AXM Universal Creation.
- **Lower layer — WALDO neural substrate:** a clean code snapshot beneath `neural/waldo/`.
- **No learned state imported:** no model weights, checkpoints, generated model state, or prior experience are seeded into this repository.
- **No hidden coupling yet:** this bootstrap establishes the physical/source boundary only. Any UC ↔ neural bridge must be explicit, inspectable, testable, and added as a later change.
- **UC remains usable without the neural layer.** The neural layer may learn from approved experience later, but must not silently become the owner of UC capabilities or canonical truth.

## Pinned source state

Exact source commits are recorded in `SOURCE_SNAPSHOTS.json`.

## Licensing / provenance

The root UC snapshot keeps its own license and provenance files. The nested WALDO snapshot keeps its own `LICENSE`, `LICENSE_BOUNDARY.md`, `NOTICE`, `THIRD_PARTY.json`, and source notices. Nesting the WALDO source here does **not** relicense it under the UC root license.

## First experiment rule

Start from this clean baseline. Let experience create the difference; do not fake a trained brain by importing old checkpoints.
