from copy import deepcopy
import json
import sys
import unittest

from axm_uc import simulation
from axm_uc.neural_simulation import CanvasFitSimulation, _packet


class CanvasSimulationTests(unittest.TestCase):
    def test_real_uc_rule_exact_replay_batch_and_snapshot(self):
        for family in CanvasFitSimulation.FAMILIES:
            provider = CanvasFitSimulation(family)
            states = [provider.reset(seed) for seed in range(8)]
            before = deepcopy(states)
            results = provider.step_many(states,[.2]*len(states))
            self.assertEqual(states,before)
            for result in results:
                body = provider.verify_transition(result['experience'])
                expected = dict(body['proposed_shape'])
                simulation._fit_shape(expected,1,1)
                self.assertEqual(expected,body['result_shape'])
                self.assertTrue(body['verification']['within_canvas'])
                self.assertEqual(provider.restore(json.loads(json.dumps(provider.snapshot(result['state'])))),result['state'])

    def test_rehashed_false_external_source_or_result_fails(self):
        provider = CanvasFitSimulation()
        packet = provider.step(provider.reset(41),.3)['experience']
        for key,value in [('experience_source','external_run'),('target',[0]*4),('raw_human_prompt','invented'),('selected_capabilities',['unknown'])]:
            body = deepcopy(packet['body'])
            body[key] = value
            with self.assertRaises(ValueError): provider.verify_transition(_packet(body))

    def test_terminal_nonfinite_and_family_mismatch_rejected(self):
        provider = CanvasFitSimulation()
        state = provider.reset(1)
        for value in (True,float('nan'),float('inf'),2):
            with self.assertRaises(ValueError): provider.step(state,value)
        with self.assertRaises(ValueError): provider.step(provider.step(state,0)['state'],0)
        with self.assertRaises(ValueError): CanvasFitSimulation('inside').step(state,0)

    def test_uc_adapter_does_not_import_the_learner(self):
        # This module's standalone suite runs without either neural repository.
        self.assertNotIn('neural.axm_brain',sys.modules)
