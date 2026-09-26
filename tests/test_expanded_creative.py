import json
from pathlib import Path
import random
import tempfile
import unittest

from tools import run_uc_expanded_creative as lab


class ExpandedCreativeTests(unittest.TestCase):
    def test_first_coverage_reaches_non_asset_creation_classes(self):
        state = {
            "family_counts": {family: 0 for family in lab.FAMILIES},
        }
        rng = random.Random(1)
        seen = []
        for _ in range(len(lab.FAMILIES)):
            family = lab.choose_family(state, rng)
            seen.append(family)
            state["family_counts"][family] += 1
        self.assertEqual(tuple(seen), lab.FAMILIES)
        self.assertIn("browser-game", seen[:4])
        self.assertIn("web-project", seen[:4])
        self.assertIn("native-visual", seen[:4])
        self.assertIn("compound-hub", seen)

    def test_requests_carry_autonomous_creative_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            ctx = {"session": "session-x", "run_index": 3, "family": "parametric-structure"}
            request = lab._parametric_structure(run_dir, random.Random(7), **ctx)[0]
        self.assertEqual(request["axm_source"]["kind"], "autonomous_creative")
        self.assertEqual(request["axm_source"]["actor"], "uc-expanded-creative")
        self.assertEqual(request["axm_source"]["metadata"]["family"], "parametric-structure")
        self.assertEqual(request["kind"], "shape-recipe-asset")

    def test_compound_hub_reuses_prior_catalog_then_packages_it(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            catalog = [
                {"run_index": 1, "family": "browser-game", "path": "creations/a/game", "steps": 1},
                {"run_index": 2, "family": "parametric-structure", "path": "creations/b/shape.glb", "steps": 1},
            ]
            ctx = {"session": "session-x", "run_index": 9, "family": "compound-hub"}
            requests = lab._compound_hub(run_dir, random.Random(5), catalog, **ctx)
        self.assertEqual([row["kind"] for row in requests], ["mixed-media-project", "portable-creation-bundle"])
        manifest = json.loads(requests[0]["inputs"]["text_files"]["manifest.json"])
        self.assertEqual(len(manifest["items"]), 2)
        self.assertEqual(requests[1]["inputs"]["source"], str(run_dir / "compound-hub"))
        self.assertEqual(requests[1]["inputs"]["operation"], "pack")

    def test_compound_can_physically_copy_prior_binary_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "prior.glb"
            source.write_bytes(b"glTF-test-binary")
            catalog = [{"run_index": 7, "family": "parametric-structure", "path": str(source), "steps": 1}]
            binaries, inventory = lab._collect_prior_binary(catalog)
        self.assertEqual(len(binaries), 1)
        self.assertEqual(len(inventory), 1)
        descriptor = next(iter(binaries.values()))
        self.assertEqual(descriptor["encoding"], "base64")
        self.assertEqual(descriptor["media_type"], "model/gltf-binary")

    def test_saved_state_is_seed_bound_and_resumable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = lab._state(path, seed=17, session="s")
            state["next_run"] = 4
            path.write_text(json.dumps(state), encoding="utf-8")
            restored = lab._state(path, seed=17, session="ignored")
            self.assertEqual(restored["next_run"], 4)
            with self.assertRaises(ValueError):
                lab._state(path, seed=18, session="ignored")

    def test_catalog_aware_software_is_real_project_request(self):
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            catalog = [{"run_index": 1, "family": "browser-game", "path": "creations/game", "steps": 1}]
            ctx = {"session": "s", "run_index": 4, "family": "web-project"}
            web = lab._web_project(run_dir, random.Random(2), catalog, **ctx)[0]
            ctx["family"] = "python-tool"
            python = lab._python_tool(run_dir, random.Random(2), catalog, **ctx)[0]
        self.assertEqual(web["kind"], "static-web-project")
        self.assertIn("browser-game", web["inputs"]["files"]["index.html"])
        self.assertEqual(python["kind"], "python-project")
        self.assertIn("HISTORY", python["inputs"]["files"]["main.py"])


if __name__ == "__main__":
    unittest.main()
