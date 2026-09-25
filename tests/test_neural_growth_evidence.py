import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from axm_uc.neural_growth import inspect_model_state, write_growth_comparison


class GrowthEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = self.root / 'models'

    def run_record(self, name, content=b'weights-v1', *, observation=None):
        directory = self.models / 'learner' / 'runs' / name
        directory.mkdir(parents=True)
        artifact = directory / 'artifacts' / 'model.safetensors'
        artifact.parent.mkdir()
        artifact.write_bytes(content)
        value = {'state': 'complete'}
        if observation is not None:
            value['observation'] = {**observation, 'artifacts': [
                {'path': 'artifacts/model.safetensors',
                 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}]}
        (directory / 'RUN.json').write_text(json.dumps(value), encoding='utf-8')
        return directory

    def status(self, before):
        return write_growth_comparison(self.root, before, inspect_model_state(self.models))['status']

    def test_missing_or_nonboolean_simulation_evidence_is_not_real(self):
        before = inspect_model_state(self.models)
        for index, observation in enumerate((None, {}, {'simulated': 0}, {'simulated': 'false'})):
            self.run_record(str(index), observation=observation)
        self.assertEqual(self.status(before), 'REAL_NEURAL_GROWTH_NOT_PROVEN')

    def test_copied_unchanged_weights_are_not_growth(self):
        self.run_record('first', observation={'simulated': False})
        before = inspect_model_state(self.models)
        self.run_record('second', observation={'simulated': False})
        self.assertEqual(self.status(before), 'REAL_NEURAL_GROWTH_NOT_PROVEN')

    def test_simulated_changes_cannot_borrow_another_runs_completion(self):
        self.run_record('first', observation={'simulated': False})
        before = inspect_model_state(self.models)
        self.run_record('real-no-change', observation={'simulated': False})
        self.run_record('simulated-change', b'different', observation={'simulated': True})
        self.assertEqual(self.status(before), 'REAL_NEURAL_GROWTH_NOT_PROVEN')

    def test_run_artifact_digest_must_match_observed_file(self):
        before = inspect_model_state(self.models)
        directory = self.run_record('bad-digest', observation={'simulated': False})
        (directory / 'artifacts' / 'model.safetensors').write_bytes(b'changed-after-run')
        self.assertEqual(self.status(before), 'REAL_NEURAL_GROWTH_NOT_PROVEN')

    def test_incomplete_json_receipt_is_not_growth(self):
        before = inspect_model_state(self.models)
        directory = self.run_record('partial', observation={'simulated': False})
        (directory / 'RUN.json').write_text('{', encoding='utf-8')
        self.assertEqual(self.status(before), 'REAL_NEURAL_GROWTH_NOT_PROVEN')

    def test_explicit_real_run_with_changed_verified_weights_is_observed(self):
        self.run_record('first', observation={'simulated': False})
        before = inspect_model_state(self.models)
        self.run_record('second', b'weights-v2', observation={'simulated': False})
        self.assertEqual(self.status(before), 'REAL_NEURAL_GROWTH_OBSERVED')

    def test_legacy_aggregate_only_comparison_cannot_claim_growth(self):
        before = inspect_model_state(self.models)
        del before['artifact_sha256']
        del before['verified_runs']
        self.run_record('real', observation={'simulated': False})
        self.assertEqual(self.status(before), 'REAL_NEURAL_GROWTH_NOT_PROVEN')

    def test_unrelated_model_cannot_supply_selected_model_growth(self):
        selected = self.models / 'selected'
        before = inspect_model_state(selected)
        self.run_record('other-model', observation={'simulated': False})
        result = write_growth_comparison(self.root, before, inspect_model_state(selected))
        self.assertEqual(result['status'], 'REAL_NEURAL_GROWTH_NOT_PROVEN')

    def test_empty_and_missing_artifacts_are_not_growth(self):
        before = inspect_model_state(self.models)
        self.run_record('empty', b'', observation={'simulated': False})
        directory = self.run_record('missing', observation={'simulated': False})
        (directory / 'artifacts' / 'model.safetensors').unlink()
        self.assertEqual(self.status(before), 'REAL_NEURAL_GROWTH_NOT_PROVEN')
