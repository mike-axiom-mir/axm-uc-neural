#!/usr/bin/env python3
from __future__ import annotations

import sys

import uc_waldo_wiring_proof as proof

_original_live_creation = proof.run_live_creation


def _compatible_live_creation(root, manifest):
    updated = dict(manifest)
    updated["observe"] = [
        {"id": row.get("id"), "kind": "exists", "path": row.get("path")}
        if row.get("type") == "file-exists"
        else row
        for row in manifest.get("observe", [])
    ]
    return _original_live_creation(root, updated)


proof.run_live_creation = _compatible_live_creation
raise SystemExit(proof.main())
