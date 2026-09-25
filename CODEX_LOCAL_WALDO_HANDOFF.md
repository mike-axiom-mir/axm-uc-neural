# Codex Local Handoff — Reuse the Existing WALMI OpenWALDO Route

**Date:** 2026-09-25

**Branch:** `codex/uc-waldo-wiring-proof-v1`

**Purpose:** make the UC/OpenWALDO weekend experiment use the *already proven local WALMI route* instead of inventing a second Windows solution.

## Important local fact

Mike reports that OpenWALDO already works for WALMI on this Windows laptop.

The pinned OpenWALDO source in this repository currently documents/implements real training as:

- Linux -> PyTorch / TorchTitan
- Apple Silicon macOS -> MLX

The pinned PyTorch resolver explicitly rejects non-Linux hosts, and automatic backend selection has no native Windows training policy.

Therefore the local WALMI setup contains information that GitHub does not.

## Your task

Before changing the UC experiment runtime, inspect the existing local WALMI/OpenWALDO setup and determine **exactly how it is running**.

Identify whether the working path is:

- native Windows with a local patch or adapter;
- WSL / Linux underneath Windows;
- a wrapper or launcher;
- a separate Python environment;
- a different WALDO binary/build;
- another compatibility layer.

Do not guess from upstream documentation if the local machine gives stronger evidence.

## Reuse, do not duplicate

If the WALMI path is genuinely working and compatible, reuse that exact local route for `axm-uc-neural`.

Preferred result:

```text
UC experiment
    ↓
existing proven WALMI/OpenWALDO local runtime
    ↓
persistent UC learner
```

Do **not** create a second training stack merely because the repository launcher is currently incomplete for Windows.

## Preserve experiment semantics

Do not change these unless a compatibility issue makes the current experiment literally unable to run:

- fake/simulated WALDO backend stays forbidden;
- neural learning link defaults OFF;
- turning neural learning ON establishes the exact current intake-sequence boundary;
- experiences gathered before that boundary are **not** silently back-trained later;
- repeated identical experiences remain separate occurrences;
- one persistent learner continues across batches;
- provenance and `trace_id` linkage remain intact;
- UC wiring diagnostics remain intact;
- neural-growth diagnostics remain intact;
- dashboard/cockpit remains read-mostly;
- the dashboard must not trigger extra continuous rendering merely for display;
- do not tune learning policy, optimizer, preset, learning rate, batching, or other experimental variables merely to improve the apparent outcome;
- real model-state change is evidence of state change, not proof of usefulness.

## Current entry point

The intended human entry remains:

`START_WEEKEND_UC_NEURAL_LAB.cmd`

After inspection, make that launcher call the proven local route where practical.

If a second helper script is unavoidable, keep the top-level launcher stable and delegate underneath it.

## Required observable result

When finished, Mike should not need to understand the runtime plumbing.

Starting the lab should make the cockpit show one of two honest states:

### READY

- dashboard starts;
- feeder starts through the proven WALMI/OpenWALDO route;
- neural link remains OFF until explicitly enabled;
- when enabled, new UC experiences can reach the real learner;
- persisted non-simulated model-state change can be observed.

### HOLD

If the proven WALMI route cannot be reused, do not silently fall back or simulate.

Leave a clear local status stating:

- what route WALMI currently uses;
- why it could not be reused;
- what dependency/runtime is missing;
- the smallest next action required.

## Do not rewrite the experiment

This handoff is about **local runtime integration**, not redesign.

Cloud-side evidence already establishes the UC -> OpenWALDO wiring and experiment semantics. The local job is to connect those semantics to the machine's already-working WALMI path.

## Truth boundary

A route that launches is not enough.

The local integration is only considered real when the learner produces a non-simulated completed run and persists changed model state under the existing growth diagnostic.

If WALMI's existing route is itself simulated or otherwise not real training, report that plainly instead of inheriting the assumption that it learns.
