from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from axm_uc.experiment_controls import read_controls, set_control
from axm_uc.neural_experience_transport import paths as neural_paths, record_uc_experience
from axm_uc.neural_growth import inspect_model_state, write_growth_comparison


ROOT = Path(__file__).resolve().parents[1]


class UCWaldoWiringProofTests(unittest.TestCase):
    def test_representative_uc_paths_reach_openwaldo_intake(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools/run_uc_waldo_wiring_proof.py"), "emit", "--root", str(ROOT), "--reset"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + "\n" + completed.stderr)
        state = ROOT / "state/neural-experiment"
        coverage = json.loads((state / "uc-wiring-coverage.json").read_text(encoding="utf-8"))
        self.assertEqual(coverage["status"], "COMPLETE")
        self.assertEqual(coverage["required_paths_received"], coverage["required_paths"])
        rows = [
            json.loads(line)
            for line in (state / "openwaldo-intake.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertIsInstance(row.get("text"), str)
            decoded = json.loads(row["text"])
            self.assertEqual(decoded["schema"], "axm.uc-neural-experience/v1")

    def test_repeated_identical_experiences_remain_distinct_occurrences(self) -> None:
        with tempfile.TemporaryDirectory() as machine_tmp:
            root = Path(machine_tmp)
            for _ in range(2):
                record_uc_experience(
                    root,
                    path_id="machine.direct",
                    event="result",
                    status="RETURNED",
                    payload={"same": "experience"},
                )
            rows = [
                json.loads(line)
                for line in neural_paths(root)["intake"].read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["text"], rows[1]["text"])
            self.assertNotEqual(rows[0]["axm"]["event_id"], rows[1]["axm"]["event_id"])
            self.assertEqual([row["axm"]["sequence"] for row in rows], [1, 2])

    def test_neural_link_enable_starts_at_current_experience_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as machine_tmp:
            root = Path(machine_tmp)
            defaults = read_controls(root)
            self.assertFalse(defaults["neural_link_enabled"])
            record_uc_experience(
                root,
                path_id="machine.direct",
                event="result",
                status="RETURNED",
                payload={"phase": "baseline-1"},
            )
            record_uc_experience(
                root,
                path_id="machine.direct",
                event="result",
                status="RETURNED",
                payload={"phase": "baseline-2"},
            )
            enabled = set_control(root, "neural_link_enabled", True)
            self.assertTrue(enabled["neural_link_enabled"])
            self.assertEqual(enabled["neural_link_start_sequence"], 2)
            record_uc_experience(
                root,
                path_id="machine.direct",
                event="result",
                status="RETURNED",
                payload={"phase": "learning-1"},
            )
            rows = [
                json.loads(line)
                for line in neural_paths(root)["intake"].read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            after_boundary = [
                row
                for row in rows
                if row.get("axm", {}).get("sequence", 0) > enabled["neural_link_start_sequence"]
            ]
            self.assertEqual(len(after_boundary), 1)
            self.assertIn("learning-1", after_boundary[0]["text"])

    def test_neural_growth_diagnostic_requires_real_complete_run(self) -> None:
        with tempfile.TemporaryDirectory() as machine_tmp, tempfile.TemporaryDirectory() as model_tmp:
            machine_root = Path(machine_tmp)
            model_root = Path(model_tmp)
            before = inspect_model_state(model_root)
            run_dir = model_root / "proof/runs/run-1"
            run_dir.mkdir(parents=True)
            (run_dir / "RUN.json").write_text(
                json.dumps({"state": "complete", "observation": {"simulated": False}}) + "\n",
                encoding="utf-8",
            )
            (run_dir / "model.safetensors").write_bytes(b"real-proof-artifact")
            after = inspect_model_state(model_root)
            result = write_growth_comparison(machine_root, before, after)
            self.assertEqual(result["status"], "REAL_NEURAL_GROWTH_OBSERVED")


if __name__ == "__main__":
    unittest.main()
