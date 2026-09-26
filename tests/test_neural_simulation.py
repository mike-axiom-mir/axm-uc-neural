from copy import deepcopy
import json
import sys
import unittest

from axm_uc import simulation
from axm_uc.neural_simulation import CanvasFitSimulation, _packet
from axm_uc.workflow_simulation import WorkflowPassSimulation, WorkflowState
from axm_uc.trajectory_simulation import WorkflowTrajectorySimulation, WorkflowTrajectoryState


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

    def test_workflow_profiles_replay_exactly_and_keep_grounded_stage_groups(self):
        for family in WorkflowPassSimulation.FAMILIES:
            provider = WorkflowPassSimulation(family)
            self.assertEqual(set(provider.stage_groups), set(WorkflowPassSimulation.ACTION_NAMES))
            self.assertTrue(all(provider.stage_groups.values()))
            states = [provider.reset(seed) for seed in range(8)]
            actions = [WorkflowPassSimulation.ACTION_VALUES[index % 4] for index in range(len(states))]
            results = provider.step_many(states, actions)
            for result in results:
                body = provider.verify_transition(result['experience'])
                self.assertEqual(body['workflow_stages'], provider.stage_groups[body['workflow_pass']])
                self.assertEqual(body['selected_capabilities'],
                                 [f"product-workflow:{family}:{stage}" for stage in body['workflow_stages']])
                self.assertTrue(body['verification']['bounded_debt'])
                self.assertEqual(provider.restore(json.loads(json.dumps(provider.snapshot(result['state'])))), result['state'])

    def test_workflow_order_exposes_upstream_rework_instead_of_fake_progress(self):
        provider = WorkflowPassSimulation('static-3d')
        state = WorkflowState(.9, .8, .7, .4, 41, 0, 'static-3d')
        surface = provider.step(state, -.25)['experience']['body']
        structure = provider.step(state, -.75)['experience']['body']
        verify = provider.step(state, .75)['experience']['body']
        self.assertFalse(surface['prerequisites_ready'])
        self.assertTrue(structure['prerequisites_ready'])
        self.assertFalse(verify['prerequisites_ready'])
        self.assertLess(structure['target'][0], surface['target'][0])
        self.assertGreaterEqual(verify['target'][3], max(state.structure, state.surface, state.detail))

    def test_workflow_packet_tampering_fails_replay(self):
        provider = WorkflowPassSimulation('image')
        packet = provider.step(provider.reset(19), .25)['experience']
        for key, value in [('workflow_pass', 'structure'), ('target', [0, 0, 0, 0]),
                           ('selected_capabilities', ['invented']), ('experience_source', 'external_run')]:
            body = deepcopy(packet['body'])
            body[key] = value
            with self.assertRaises(ValueError):
                provider.verify_transition(_packet(body))

    def test_workflow_trajectory_has_intermediate_steps_and_terminal_reward_only(self):
        provider = WorkflowTrajectorySimulation('game')
        state = provider.reset(41)
        rewards = []
        for index in range(provider.HORIZON):
            result = provider.step(state, WorkflowTrajectorySimulation.ACTION_VALUES[index % 4])
            body = provider.verify_transition(result['experience'])
            self.assertEqual(body['trajectory_step'], index)
            self.assertEqual(body['terminal'], index + 1 == provider.HORIZON)
            rewards.append(body['reward'])
            state = result['state']
        self.assertTrue(all(value is None for value in rewards[:-1]))
        self.assertIsInstance(rewards[-1], float)
        self.assertGreaterEqual(rewards[-1], -1)
        self.assertLessEqual(rewards[-1], 1)
        with self.assertRaises(ValueError):
            provider.step(state, 0)

    def test_workflow_trajectory_tamper_and_snapshot_fail_closed(self):
        provider = WorkflowTrajectorySimulation('image')
        state = provider.reset(7)
        packet = provider.step(state, .75)['experience']
        body = deepcopy(packet['body'])
        body['trajectory_step'] = 99
        with self.assertRaises(ValueError):
            provider.verify_transition(_packet(body))
        snapshot = provider.snapshot(state)
        self.assertEqual(provider.restore(json.loads(json.dumps(snapshot))), state)
        bad = deepcopy(snapshot)
        bad['body']['state']['step'] = 99
        with self.assertRaises(ValueError):
            provider.restore(_packet(bad['body']))

    def test_uc_adapter_does_not_import_the_learner(self):
        # This module's standalone suite runs without either neural repository.
        self.assertNotIn('neural.axm_brain',sys.modules)
