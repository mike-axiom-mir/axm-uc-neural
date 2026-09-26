import tempfile
from pathlib import Path
import unittest

from tools import run_uc_workflow_practice as lab


class WorkflowPracticeLabTests(unittest.TestCase):
    def test_profiles_are_bounded_real_workflow_requests(self):
        requests = lab.requests()
        self.assertEqual(set(requests), set(lab.PROFILE_NAMES))
        for name, request in requests.items():
            self.assertEqual(request["schema"], "axm.workflow-experiment/v0.1", name)
            self.assertTrue(request["intent"])
            self.assertGreaterEqual(request["budget"]["trials"], 1)
            self.assertLessEqual(request["budget"]["trials"], 16)
            self.assertGreaterEqual(request["budget"]["confirmation_cases"], 1)
            self.assertTrue(request["goals"])

    def test_default_memory_is_creation_output_not_machine_state(self):
        relative = lab.BASE.relative_to(lab.ROOT)
        self.assertEqual(relative.parts[0], "creations")
        self.assertNotIn("state", relative.parts[:1])

    def test_next_run_never_reuses_an_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first = lab._next_run("vent-hood", base)
            self.assertEqual(first.name, "run-0001")
            first.mkdir()
            second = lab._next_run("vent-hood", base)
            self.assertEqual(second.name, "run-0002")
            (first.parent / "notes").mkdir()
            self.assertEqual(lab._next_run("vent-hood", base).name, "run-0002")


if __name__ == "__main__":
    unittest.main()
