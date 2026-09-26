from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from neural.axm_brain.simulation_session import SimulationSession
from neural.axm_brain.state import verify_snapshot
from tools.run_uc_simulation_lab import fresh_session, providers, atomic_write, checkpoint_lock, workflow_route_evaluation


class UCDirectSimulationTests(unittest.TestCase):
    def test_uc_and_workflow_experience_survive_learning_and_disk_restore(self):
        session = fresh_session()
        parent = deepcopy(session.parent)
        before = session.evaluate()
        routing_before = workflow_route_evaluation(session)
        session.advance(768)
        after = session.evaluate()
        routing_after = workflow_route_evaluation(session)
        self.assertLess(after['mean_family_mse'], before['mean_family_mse'])
        for family in ('inside', 'overflow', 'mixed'):
            self.assertLess(after['families'][family]['mse'], before['families'][family]['mse'])
        self.assertEqual(routing_before['probes'], 256)
        self.assertEqual(routing_after['probes'], 256)
        self.assertEqual(set(routing_after['families']),
                         {'workflow-static-3d','workflow-animated-3d','workflow-game','workflow-image'})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json'
            atomic_write(path,session.to_snapshot())
            restored = SimulationSession.from_snapshot(json.loads(path.read_text()),providers())
        self.assertEqual(restored.evaluate(), after)
        self.assertEqual(workflow_route_evaluation(restored), routing_after)
        self.assertEqual(restored.parent, parent)
        restored.advance(3)
        session.advance(3)
        self.assertEqual(restored.to_snapshot(), session.to_snapshot())
        self.assertEqual(session.learner.host_experience_count, 771)
        self.assertTrue(all(event.source=='deterministic_simulation' for event in session.learner.replay))

    def test_one_provider_failure_cannot_partially_replace_saved_state(self):
        session = fresh_session()
        session.advance(3)
        before = session.to_snapshot()
        class Broken:
            def __getattr__(self,key): return getattr(original,key)
            def step(self,state,action): raise ValueError('deliberate provider failure')
        names = list(session.providers)
        next_name = names[len(session.records) % len(names)]
        original = session.providers[next_name]
        session.providers[next_name] = Broken()
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
