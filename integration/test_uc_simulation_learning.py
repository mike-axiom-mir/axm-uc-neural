from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from neural.axm_brain.simulation_session import SimulationSession
from neural.axm_brain.state import verify_snapshot
from tools.run_uc_simulation_lab import fresh_session, providers, atomic_write, checkpoint_lock


class UCDirectSimulationTests(unittest.TestCase):
    def test_actual_uc_rule_teaches_unseen_examples_and_survives_disk_restore(self):
        session = fresh_session()
        parent = deepcopy(session.parent)
        before = session.evaluate()
        session.advance(384)
        after = session.evaluate()
        self.assertLess(after['mean_family_mse'],before['mean_family_mse']*.5)
        for family in before['families']:
            self.assertLess(after['families'][family]['mse'],before['families'][family]['mse'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json'
            atomic_write(path,session.to_snapshot())
            restored = SimulationSession.from_snapshot(json.loads(path.read_text()),providers())
        self.assertEqual(restored.evaluate(),after)
        self.assertEqual(restored.parent,parent)
        restored.advance(3)
        session.advance(3)
        self.assertEqual(restored.to_snapshot(),session.to_snapshot())
        self.assertEqual(session.learner.host_experience_count,387)
        self.assertTrue(all(event.source=='deterministic_simulation' for event in session.learner.replay))

    def test_one_provider_failure_cannot_partially_replace_saved_state(self):
        session = fresh_session()
        session.advance(3)
        before = session.to_snapshot()
        class Broken:
            def __getattr__(self,key): return getattr(original,key)
            def step(self,state,action): raise ValueError('deliberate provider failure')
        original = session.providers['overflow']
        session.providers['overflow'] = Broken()
        with self.assertRaises(ValueError): session.advance(3)
        self.assertEqual(before,session.to_snapshot())

    def test_scheduler_uses_training_error_without_consuming_evaluation(self):
        session = fresh_session(policy='error_guided')
        session.advance(30)
        self.assertEqual(sum(session.counts.values()),30)
        before = session.to_snapshot()
        session.evaluate()
        self.assertEqual(before,session.to_snapshot())
        self.assertTrue(session.reproduce())

    def test_concurrent_writer_is_held_and_checkpoint_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json'
            path.write_text('existing learner')
            with checkpoint_lock(path):
                with self.assertRaises(ValueError):
                    with checkpoint_lock(path): self.fail('second writer entered')
            self.assertEqual(path.read_text(),'existing learner')
            with checkpoint_lock(path): pass
