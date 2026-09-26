#!/usr/bin/env python3
"""Expanded UC Creative Mode experiment across multiple creation classes.

This host deliberately exercises existing UC capabilities rather than inventing a
new creator. It grows a caller-owned catalog under creations/, revisits different
creation classes, and occasionally composes prior successful outputs into a new
local hub/project + portable bundle.

The scheduler is deterministic from seed + run index. It is exploration, not an
aesthetic judge. UC capability results remain authoritative for what succeeded.
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from axm_uc.atomic import atomic_write_json
from axm_uc.experiment_controls import read_controls
from axm_uc.machine import UniversalCreationMachine

DEFAULT_BASE = ROOT / "creations" / "neural-experiment" / "expanded-creative"
STATE_SCHEMA = "axm.expanded-creative-state/v1"
FAMILIES = (
    "parametric-structure",
    "browser-game",
    "web-project",
    "native-visual",
    "material-product",
    "textured-3d-product",
    "creative-flow-mesh",
    "python-tool",
    "compound-hub",
)
PALETTES = (
    ("#10212b", "#294c5b", "#8ff0d2", "#ffca6c", "#ef7180"),
    ("#171322", "#3d315b", "#a78bfa", "#f7c66d", "#f472b6"),
    ("#101b18", "#254a3f", "#8ae8af", "#ffd166", "#ef6f6c"),
    ("#171b24", "#343f55", "#72d9ff", "#ffb86b", "#ff6f91"),
)
RGB = (
    (62, 147, 157),
    (197, 112, 55),
    (104, 86, 174),
    (70, 145, 92),
    (176, 72, 92),
)


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _source(session: str, run_index: int, family: str) -> dict:
    return {
        "kind": "autonomous_creative",
        "actor": "uc-expanded-creative",
        "interface": "tools/run_uc_expanded_creative.py",
        "session_id": session,
        "source_event_id": f"creative-{run_index:06d}",
        "note": "Bounded experimental Creative Mode exploration using existing UC capabilities.",
        "metadata": {"family": family, "run_index": run_index},
    }


def _safe_id(text: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in text).strip("-")[:80] or "creation"


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _tree_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    for current, dirs, files in os.walk(path):
        dirs[:] = [name for name in dirs if name not in {".git", "__pycache__"}]
        for name in files:
            try:
                total += (Path(current) / name).stat().st_size
            except OSError:
                pass
    return total


def _state(path: Path, *, seed: int, session: str) -> dict:
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != STATE_SCHEMA:
            raise ValueError("unsupported expanded-creative state")
        if value.get("seed") != seed:
            raise ValueError("saved creative state uses a different seed; choose another --base or the original seed")
        return value
    return {
        "schema": STATE_SCHEMA,
        "seed": seed,
        "session": session,
        "next_run": 0,
        "bytes_created": 0,
        "runs": [],
        "catalog": [],
        "family_counts": {family: 0 for family in FAMILIES},
        "automatic_canon_admission": False,
    }


def _request_base(request: dict, *, session: str, run_index: int, family: str) -> dict:
    value = copy.deepcopy(request)
    value["axm_source"] = _source(session, run_index, family)
    return value


def _parametric_structure(run_dir: Path, rng: random.Random, **ctx) -> list[dict]:
    count = rng.randint(2, 6)
    gap = round(rng.uniform(.55, 1.25), 3)
    upper = rng.randint(2, 5)
    color_bias = round(rng.uniform(.15, .7), 3)
    request = {
        "kind": "shape-recipe-asset",
        "direction": "Explore a reusable parametric structure from retained shape causes.",
        "inputs": {
            "path": str(run_dir / "structure.glb"),
            "recipe": {
                "schema": "axm.shape-recipe/v0.1",
                "name": f"Creative lattice {ctx['run_index']}",
                "definitions": {
                    "rail": {
                        "vars": {"count": count, "gap": gap},
                        "parts": [{
                            "repeat": ["var", "count"], "as": "i",
                            "body": [{"shape": "box", "size": [.38, .22, .30],
                                      "pos": [["*", ["var", "gap"], ["var", "i"]], 0, 0]}],
                        }],
                    }
                },
                "paint": {
                    "vars": {"span": max(2.0, count * gap)},
                    "color": [
                        ["min", 1, ["max", 0, ["/", ["+", ["var", "x"], 2], ["var", "span"]]]],
                        color_bias,
                        ["if", [">", ["var", "y"], .8], .9, .3],
                    ],
                },
                "parts": [
                    {"use": "rail", "with": {"count": count}, "pos": [0, 0, 0]},
                    {"use": "rail", "with": {"count": upper}, "pos": [0, 1.4, 0], "scale": .65},
                ],
            },
        },
    }
    return [_request_base(request, **ctx)]


def _material_product(run_dir: Path, rng: random.Random, **ctx) -> list[dict]:
    request = _load("examples/requests/product-workflow-material.json")
    request["inputs"]["path"] = str(run_dir / "material")
    request["inputs"]["run_id"] = f"creative-material-{ctx['run_index']:06d}"
    request["inputs"]["brief"]["purpose"] = f"Explore reusable painted material variant {ctx['run_index']}"
    recipe = request["inputs"]["recipe"]["paint"]
    recipe["seed"] = rng.randrange(1, 1_000_000)
    recipe["color"] = list(rng.choice(RGB))
    recipe["layer"] = {"amount": round(rng.uniform(.08, .42), 3),
                       "substrate_rgb": list(rng.choice(RGB))}
    return [_request_base(request, **ctx)]


def _textured_product(run_dir: Path, rng: random.Random, **ctx) -> list[dict]:
    request = _load("examples/requests/product-workflow-blender.json")
    inputs = request["inputs"]
    inputs["path"] = str(run_dir / "textured-product")
    inputs["run_id"] = f"creative-prop-{ctx['run_index']:06d}"
    inputs.pop("production", None)
    inputs["brief"] = {
        "purpose": f"Explore a complete textured 3D product {ctx['run_index']}",
        "target": "UC native offline textured GLB + deterministic previews",
        "quality_intent": "Readable form, reusable material causes, UV evidence and two-light inspection",
    }
    scale = rng.uniform(.6, 1.5)
    primitive = inputs["specification"]["primitives"][0]
    primitive["positions"] = [[round(value * scale, 6) for value in point] for point in primitive["positions"]]
    recipe = inputs["recipe"]["paint"]
    recipe["seed"] = rng.randrange(1, 1_000_000)
    recipe["color"] = list(rng.choice(RGB))
    inputs["preview"] = {"width": 160, "height": 120}
    return [_request_base(request, **ctx)]


def _browser_game(run_dir: Path, rng: random.Random, **ctx) -> list[dict]:
    request = _load("examples/requests/create_outpost.json")
    spec = request["inputs"]["specification"]
    request["inputs"]["path"] = str(run_dir / "game")
    spec["id"] = f"creative-outpost-{ctx['run_index']:06d}"
    spec["title"] = f"Creative Outpost {ctx['run_index']:04d}"
    bg, ground, accent, player, danger = rng.choice(PALETTES)
    spec["theme"].update(background=bg, ground=ground, panel=ground, accent=accent, danger=danger, text="#f5f7fb")
    spec["player"]["color"] = player
    spec["player"]["speed"] = rng.randint(210, 310)
    spec["rules"]["projectile_damage"] = rng.randint(22, 42)
    spec["construction"]["initial_credits"] = rng.randint(140, 280)
    spec["waves"]["clear_bonus"] = rng.randint(40, 90)
    request["direction"] = "Explore a self-contained playable browser-game variation using UC game machinery."
    return [_request_base(request, **ctx)]


def _web_project(run_dir: Path, rng: random.Random, catalog: list[dict], **ctx) -> list[dict]:
    recent = catalog[-8:]
    rows = "".join(
        f'<li><strong>{item["family"]}</strong> — {item["path"]}</li>'
        for item in recent
    ) or "<li>No earlier successful creation in this session yet.</li>"
    bg, panel, accent, warm, danger = rng.choice(PALETTES)
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>UC Creative Field {ctx['run_index']}</title><link rel="stylesheet" href="style.css"></head>
<body><main><p class="tag">AXM UC EXPANDED CREATIVE</p><h1>Field {ctx['run_index']:04d}</h1>
<p>This local page was created as software during the same exploration that creates assets, games and visual runtimes.</p>
<button id="pulse">combine signal</button><output id="out">idle</output>
<h2>Recent machine creations</h2><ul>{rows}</ul></main><script src="app.js"></script></body></html>"""
    css = f"""*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:{bg};color:#f5f7fb;font:16px system-ui}}
main{{width:min(820px,92vw);padding:42px;border-radius:26px;background:{panel};border:1px solid {accent}}}
.tag{{color:{accent};letter-spacing:.16em}}h1{{font-size:clamp(3rem,9vw,7rem);margin:.1em 0}}button{{padding:12px 18px;border-radius:999px;border:0;background:{warm};color:#111}}output{{margin-left:14px;color:{accent}}li{{margin:.55em 0}}"""
    js = """const b=document.querySelector('#pulse'),o=document.querySelector('#out');let n=0;
b.addEventListener('click',()=>{n+=1;o.textContent='combination '+n+' observed';});"""
    request = {
        "kind": "static-web-project",
        "direction": "Create a local interactive field report that incorporates the current creative catalog.",
        "inputs": {
            "path": str(run_dir / "web"),
            "project_type": "static-web",
            "files": {"index.html": html, "style.css": css, "app.js": js},
            "checks": [
                {"type": "contains", "path": "index.html", "text": "AXM UC EXPANDED CREATIVE"},
                {"type": "html-local-links", "path": "index.html"},
                {"type": "nonempty", "path": "app.js"},
            ],
        },
    }
    return [_request_base(request, **ctx)]


def _native_visual(run_dir: Path, rng: random.Random, **ctx) -> list[dict]:
    del rng
    request = {
        "kind": "native-visual-runtime",
        "direction": "Create an executable coded visual scene rather than a static asset.",
        "inputs": {"operation": "demo", "path": str(run_dir / "native-visual")},
    }
    return [_request_base(request, **ctx)]


def _creative_flow(run_dir: Path, rng: random.Random, **ctx) -> list[dict]:
    request = _load("examples/requests/creative_flow_mesh.json")
    request["direction"] = "Explore a multi-hand mesh composition and retain its candidate state receipt."
    request["inputs"]["goal"] = f"create edited mesh experiment {ctx['run_index']} and inspect bounds"
    request["inputs"]["state"]["request_label"] = f"expanded-creative-{ctx['run_index']:06d}"
    for step in request["inputs"]["steps"]:
        if step["id"] == "plane":
            step["args"]["spec"]["id"] = f"creative-plane-{ctx['run_index']:06d}"
            step["args"]["spec"]["detail"] = rng.randint(3, 9)
        elif step["id"] == "extrude":
            step["args"]["spec"]["distance"] = round(rng.uniform(.15, .85), 3)
        elif step["id"] == "shear":
            step["args"]["spec"]["factor"] = round(rng.uniform(-.45, .45), 3)
    return [_request_base(request, **ctx)]


def _python_tool(run_dir: Path, rng: random.Random, catalog: list[dict], **ctx) -> list[dict]:
    kinds = [item["family"] for item in catalog[-16:]]
    embedded = json.dumps(kinds)
    threshold = rng.randint(2, 7)
    code = f"""import json
HISTORY = {embedded!r}
THRESHOLD = {threshold}
def summarize():
    rows=json.loads(HISTORY)
    counts={{}}
    for item in rows: counts[item]=counts.get(item,0)+1
    return {{"creation_classes":counts,"distinct":len(counts),"threshold":THRESHOLD,"combined":len(counts)>=THRESHOLD}}
if __name__=="__main__": print(json.dumps(summarize(),sort_keys=True))
"""
    request = {
        "kind": "python-project",
        "direction": "Create a small inspectable software tool from the current creative-session history.",
        "inputs": {
            "path": str(run_dir / "python-tool"),
            "project_type": "python",
            "files": {"main.py": code},
            "checks": [{"type": "python-compile", "path": "main.py"}],
        },
    }
    return [_request_base(request, **ctx)]


def _collect_prior_binary(catalog: list[dict], *, allowed_root: Path | None = None) -> tuple[dict, list[dict]]:
    """Copy a bounded sample of earlier binary creations into the next compound."""
    media = {
        ".glb": "model/gltf-binary",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".wav": "audio/wav",
    }
    allowed_root = (ROOT / "creations").resolve() if allowed_root is None else Path(allowed_root).resolve()
    binaries = {}
    inventory = []
    total = 0
    maximum_total = 4 * 1024 * 1024  # keep machine request/provenance below the 8 MiB intake bound
    maximum_file = 1024 * 1024
    for item in reversed(catalog[-24:]):
        raw = Path(item["path"])
        target = (raw if raw.is_absolute() else ROOT / raw).resolve()
        try:
            target.relative_to(allowed_root)
        except ValueError:
            continue
        if not target.exists():
            continue
        candidates = [target] if target.is_file() else sorted(
            path for path in target.rglob("*") if path.is_file() and path.suffix.casefold() in media
        )
        for file in candidates:
            suffix = file.suffix.casefold()
            if suffix not in media:
                continue
            try:
                size = file.stat().st_size
            except OSError:
                continue
            if size <= 0 or size > maximum_file or total + size > maximum_total:
                continue
            body = file.read_bytes()
            name = f'assets/{int(item["run_index"]):06d}-{_safe_id(item["family"])}-{_safe_id(file.stem)}{suffix}'
            if name in binaries:
                continue
            binaries[name] = {
                "encoding": "base64",
                "content": base64.b64encode(body).decode("ascii"),
                "media_type": media[suffix],
            }
            inventory.append({
                "family": item["family"],
                "source": item["path"],
                "file": file.name,
                "copied_as": name,
                "bytes": size,
            })
            total += size
            if len(binaries) >= 12 or total >= maximum_total:
                return binaries, inventory
    return binaries, inventory


def _compound_hub(run_dir: Path, rng: random.Random, catalog: list[dict], **ctx) -> list[dict]:
    if len(catalog) < 2:
        return _web_project(run_dir, rng, catalog, **ctx)
    chosen = catalog[-min(12, len(catalog)):]
    hub = run_dir / "compound-hub"
    binaries, copied = _collect_prior_binary(chosen)
    items = []
    for item in chosen:
        raw = Path(item["path"])
        target = (raw if raw.is_absolute() else ROOT / raw).resolve()
        try:
            target.relative_to((ROOT / "creations").resolve())
        except ValueError:
            continue
        rel = os.path.relpath(target, hub).replace(os.sep, "/")
        items.append({"family": item["family"], "path": item["path"], "relative": rel})
    catalog_rows = "".join(
        f'<li><span>{row["family"]}</span><code>{row["relative"]}</code></li>' for row in items
    )
    copied_rows = "".join(
        f'<li><a href="{row["copied_as"]}">{row["family"]} — {row["file"]}</a> <small>{row["bytes"]} bytes</small></li>'
        for row in copied
    ) or "<li>No bounded binary realization was small enough to copy into this compound.</li>"
    bg, panel, accent, warm, danger = rng.choice(PALETTES)
    manifest = json.dumps({
        "schema": "axm.expanded-creative-compound/v2",
        "catalog": items,
        "physically_copied_realizations": copied,
    }, indent=2)
    text_files = {
        "index.html": f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>UC Compound</title><link rel="stylesheet" href="style.css"></head><body><main><p>UC CROSS-CAPABILITY COMPOUND</p><h1>Compound {ctx["run_index"]:04d}</h1><h2>Session catalog</h2><ul>{catalog_rows}</ul><h2>Copied realizations inside this project</h2><ul>{copied_rows}</ul><button id="b">inspect combination</button><output id="o"></output></main><script src="app.js"></script></body></html>',
        "style.css": f'body{{margin:0;min-height:100vh;display:grid;place-items:center;background:{bg};color:#fff;font:16px system-ui}}main{{width:min(900px,92vw);padding:40px;background:{panel};border:1px solid {accent};border-radius:24px}}code{{display:block;color:{accent}}a{{color:{warm}}}button{{background:{warm};padding:10px 16px;border:0;border-radius:999px}}',
        "app.js": 'document.querySelector("#b").onclick=()=>document.querySelector("#o").textContent="software + catalog + copied binary creations combined";',
        "manifest.json": manifest,
    }
    request = {
        "kind": "mixed-media-project",
        "direction": "Physically combine prior UC binary creations with new software in one validated mixed project.",
        "inputs": {
            "path": str(hub),
            "project_type": "static-web",
            "text_files": text_files,
            "binary_files": binaries,
            "checks": [
                {"type": "contains", "path": "index.html", "text": "UC CROSS-CAPABILITY COMPOUND"},
                {"type": "json-valid", "path": "manifest.json"},
                {"type": "html-local-links", "path": "index.html"},
            ],
        },
    }
    first = _request_base(request, **ctx)
    second = _request_base({
        "kind": "portable-creation-bundle",
        "direction": "Package the newly combined mixed project through a second UC capability.",
        "inputs": {
            "operation": "pack",
            "path": str(run_dir / "compound-hub.axm.zip"),
            "source": str(hub),
            "project_type": "static-web",
            "name": f"UC expanded creative compound {ctx['run_index']}",
        },
    }, **ctx)
    return [first, second]


BUILDERS = {
    "parametric-structure": _parametric_structure,
    "material-product": _material_product,
    "textured-3d-product": _textured_product,
    "browser-game": _browser_game,
    "web-project": _web_project,
    "native-visual": _native_visual,
    "creative-flow-mesh": _creative_flow,
    "python-tool": _python_tool,
    "compound-hub": _compound_hub,
}


def choose_family(state: dict, rng: random.Random) -> str:
    missing = [family for family in FAMILIES if state["family_counts"].get(family, 0) == 0]
    if missing:
        return missing[0]
    weighted = [
        "compound-hub", "compound-hub", "textured-3d-product", "browser-game",
        "web-project", "parametric-structure", "material-product", "native-visual",
        "creative-flow-mesh", "python-tool",
    ]
    return rng.choice(weighted)


def _creation_path(request: dict, run_dir: Path) -> str:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    value = inputs.get("path")
    if isinstance(value, str):
        return _relative(Path(value))
    return _relative(run_dir)


def recover_next_run_if_needed(base: Path, state: dict, *, seed: int) -> dict | None:
    """Recover a completed receipt or preserve one interrupted run directory."""
    index = int(state["next_run"])
    family_rng = random.Random((seed << 32) ^ index ^ 0xA8C54E31)
    family = choose_family(state, family_rng)
    run_dir = base / "runs" / f"run-{index:06d}-{_safe_id(family)}"
    if not run_dir.exists():
        return None

    receipt_path = run_dir / "receipt.json"
    receipt = None
    if receipt_path.is_file():
        try:
            candidate = json.loads(receipt_path.read_text(encoding="utf-8"))
            if (candidate.get("schema") == "axm.expanded-creative-run/v1"
                    and candidate.get("run_index") == index
                    and candidate.get("family") == family):
                receipt = candidate
        except (OSError, json.JSONDecodeError):
            receipt = None

    created_bytes = _tree_bytes(run_dir)
    if receipt is not None:
        success = receipt.get("success") is True
        steps = receipt.get("steps") if isinstance(receipt.get("steps"), list) else []
        if success and steps:
            state["catalog"].append({
                "run_index": index,
                "family": family,
                "path": steps[-1].get("path", _relative(run_dir)),
                "steps": len(steps),
            })
            state["catalog"] = state["catalog"][-4096:]
        recovery = {
            "run_index": index,
            "family": family,
            "success": success,
            "bytes": created_bytes,
            "receipt": _relative(receipt_path),
            "recovered_after_state_gap": True,
        }
    else:
        recovery = {
            "run_index": index,
            "family": family,
            "success": False,
            "bytes": created_bytes,
            "receipt": None,
            "interrupted_preserved": True,
        }
        atomic_write_json(run_dir / "interrupted-recovery.json", {
            "schema": "axm.expanded-creative-interruption/v1",
            "run_index": index,
            "family": family,
            "bytes_preserved": created_bytes,
            "action": "preserved-and-advanced-without-overwrite",
        })

    state["runs"].append(recovery)
    state["runs"] = state["runs"][-4096:]
    state["family_counts"][family] = int(state["family_counts"].get(family, 0)) + 1
    state["next_run"] = index + 1
    state["bytes_created"] = int(state.get("bytes_created", 0)) + created_bytes
    return recovery


def run_one(machine: UniversalCreationMachine, base: Path, state: dict, *, seed: int) -> dict:
    index = int(state["next_run"])
    family_rng = random.Random((seed << 32) ^ index ^ 0xA8C54E31)
    family = choose_family(state, family_rng)
    run_dir = base / "runs" / f"run-{index:06d}-{_safe_id(family)}"
    if run_dir.exists():
        raise ValueError(f"expanded creative run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    ctx = {"session": state["session"], "run_index": index, "family": family}
    builder = BUILDERS[family]
    kwargs = {"catalog": state["catalog"]} if family in {"web-project", "python-tool", "compound-hub"} else {}
    requests = builder(run_dir, family_rng, **kwargs, **ctx)
    results = []
    all_success = True
    for sequence, request in enumerate(requests):
        result = machine.create(request)
        atomic_write_json(run_dir / f"result-{sequence:02d}.json", result)
        success = result.get("type") == "CREATION_RESULT"
        all_success = all_success and success
        results.append({
            "sequence": sequence,
            "kind": request.get("kind"),
            "success": success,
            "capability": result.get("capability"),
            "result_type": result.get("type"),
            "path": _creation_path(request, run_dir),
        })
        if not success:
            break
    created_bytes = _tree_bytes(run_dir)
    receipt = {
        "schema": "axm.expanded-creative-run/v1",
        "run_index": index,
        "family": family,
        "success": all_success,
        "steps": results,
        "bytes": created_bytes,
        "automatic_canon_admission": False,
        "truth": "Existing UC capabilities executed by a seeded exploratory host; no aesthetic quality inference.",
    }
    atomic_write_json(run_dir / "receipt.json", receipt)
    if all_success:
        primary = results[-1]["path"] if results else _relative(run_dir)
        state["catalog"].append({
            "run_index": index,
            "family": family,
            "path": primary,
            "steps": len(results),
        })
        state["catalog"] = state["catalog"][-4096:]
    state["runs"].append({
        "run_index": index,
        "family": family,
        "success": all_success,
        "bytes": created_bytes,
        "receipt": _relative(run_dir / "receipt.json"),
    })
    state["runs"] = state["runs"][-4096:]
    state["family_counts"][family] = int(state["family_counts"].get(family, 0)) + 1
    state["next_run"] = index + 1
    state["bytes_created"] = int(state.get("bytes_created", 0)) + created_bytes
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--hours", type=float, default=8.0, help="active creative hours; paused control time does not count")
    parser.add_argument("--max-bytes", type=int, default=100_000_000_000, help="hard accumulated experiment-output ceiling")
    parser.add_argument("--max-runs", type=int, default=100000)
    parser.add_argument("--follow-control", action="store_true", help="pause while dashboard uc_creative_enabled is false")
    args = parser.parse_args(argv)
    if not 0 < args.hours <= 72:
        parser.error("--hours must be in (0, 72]")
    if not 1_000_000 <= args.max_bytes <= 2_000_000_000_000:
        parser.error("--max-bytes must be between 1 MB and 2 TB")
    if not 1 <= args.max_runs <= 1_000_000:
        parser.error("--max-runs must be in [1, 1000000]")

    base = args.base.resolve()
    base.mkdir(parents=True, exist_ok=True)
    state_path = base / "state.json"
    session = f"expanded-creative-{args.seed}"
    state = _state(state_path, seed=args.seed, session=session)
    machine = UniversalCreationMachine(ROOT)
    recovered = recover_next_run_if_needed(base, state, seed=args.seed)
    if recovered is not None:
        atomic_write_json(state_path, state)
        print(json.dumps({"recovered": recovered}), flush=True)
    active_started = time.monotonic()
    paused_total = 0.0
    pause_started = None

    try:
        while int(state["next_run"]) < args.max_runs and state["bytes_created"] < args.max_bytes:
            if args.follow_control and not read_controls(ROOT).get("uc_creative_enabled", False):
                if pause_started is None:
                    pause_started = time.monotonic()
                time.sleep(1)
                continue
            if pause_started is not None:
                paused_total += time.monotonic() - pause_started
                pause_started = None
            active_elapsed = time.monotonic() - active_started - paused_total
            if active_elapsed >= args.hours * 3600:
                break
            receipt = run_one(machine, base, state, seed=args.seed)
            atomic_write_json(state_path, state)
            print(json.dumps({
                "run": receipt["run_index"],
                "family": receipt["family"],
                "success": receipt["success"],
                "bytes": receipt["bytes"],
                "total_bytes": state["bytes_created"],
                "catalog": len(state["catalog"]),
            }), flush=True)
    except KeyboardInterrupt:
        atomic_write_json(state_path, state)
        print("\nPaused by user; state saved.", file=sys.stderr)
    finally:
        atomic_write_json(state_path, state)

    summary = {
        "status": "SAVED",
        "base": _relative(base),
        "runs_total": state["next_run"],
        "retained_run_receipts": len(state["runs"]),
        "successful_catalog_entries": len(state["catalog"]),
        "bytes_created": state["bytes_created"],
        "family_counts": state["family_counts"],
        "next_run": state["next_run"],
        "stopped_by": (
            "byte_ceiling" if state["bytes_created"] >= args.max_bytes
            else "run_ceiling" if int(state["next_run"]) >= args.max_runs
            else "time_or_controlled_stop"
        ),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        raise SystemExit(2)
