import copy
import unittest

from neural.axm_brain import (
    AXMBrain,
    AXM_ROOTS,
    BrainConfig,
    Experience,
    GenesisAdmission,
    GenesisAdmissionError,
    GenesisCandidate,
    GenesisRecord,
)


class GenesisTests(unittest.TestCase):
    def brain(self, seed=101):
        return AXMBrain(
            BrainConfig(
                input_size=2,
                hidden_size=4,
                output_size=1,
                seed=seed,
                replay_capacity=8,
            )
        )

    def candidate(self, brain=None, lineage="fixture-neural"):
        brain = brain or self.brain()
        return GenesisCandidate(
            lineage=lineage,
            brain_snapshot=brain.to_snapshot(),
            provenance={
                "source": "test-fixture",
                "trained_weights_imported": False,
                "learned_state_imported": False,
            },
            identities_roles={
                "system": "AXM Direct Brain",
                "role": "neural-specialist-substrate",
            },
            platform_assumptions={
                "runtime": "python",
                "numeric_model": "python-float",
            },
        )

    def admit(self, candidate=None):
        return GenesisAdmission.admit(
            candidate or self.candidate(),
            admitting_authority="fixture-admission",
            commit_evidence="fixture:durable-commit",
        )

    def test_virgin_neural_state_can_become_genesis(self):
        record = self.admit()
        record.verify()
        self.assertTrue(
            record.genesis_id.startswith("g0:fixture-neural:")
        )

    def test_genesis_contains_exact_four_roots(self):
        record = self.admit()
        names = tuple(
            item["name"]
            for item in record.manifest["roots"]["contract"]["roots"]
        )
        self.assertEqual(names, AXM_ROOTS)

    def test_same_birth_and_evidence_make_same_genesis_id(self):
        first = self.admit(self.candidate(self.brain(seed=9)))
        second = self.admit(self.candidate(self.brain(seed=9)))
        self.assertEqual(first.genesis_id, second.genesis_id)

    def test_different_seed_makes_different_genesis_id(self):
        first = self.admit(self.candidate(self.brain(seed=9)))
        second = self.admit(self.candidate(self.brain(seed=10)))
        self.assertNotEqual(first.genesis_id, second.genesis_id)

    def test_experienced_brain_cannot_be_admitted_as_g0(self):
        brain = self.brain()
        brain.experience(
            Experience([0.1, 0.2], target=[0.3])
        )
        with self.assertRaises(GenesisAdmissionError):
            self.admit(self.candidate(brain))

    def test_slept_brain_cannot_be_admitted_as_g0(self):
        brain = self.brain()
        brain.sleep()
        with self.assertRaises(GenesisAdmissionError):
            self.admit(self.candidate(brain))

    def test_commit_evidence_is_required(self):
        with self.assertRaises(GenesisAdmissionError):
            GenesisAdmission.admit(
                self.candidate(),
                admitting_authority="fixture",
                commit_evidence="",
            )

    def test_tampered_record_is_rejected(self):
        record = self.admit()
        data = copy.deepcopy(record.to_dict())
        data["manifest"]["lineage"] = "forged-lineage"
        with self.assertRaises(GenesisAdmissionError):
            GenesisRecord.from_dict(data)

    def test_validly_rehashed_wrong_root_brain_is_rejected(self):
        brain = self.brain()
        snapshot = brain.to_snapshot()
        body = copy.deepcopy(snapshot["body"])
        body["roots"]["contract"]["roots"][0]["name"] = "NOT_TRUTH"

        import hashlib
        import json

        digest = hashlib.sha256(
            json.dumps(
                body,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        forged = {"body": body, "sha256": digest}

        with self.assertRaises(GenesisAdmissionError):
            self.admit(
                GenesisCandidate(
                    lineage="fixture-neural",
                    brain_snapshot=forged,
                    provenance={"source": "fixture"},
                    identities_roles={"system": "fixture"},
                    platform_assumptions={"runtime": "fixture"},
                )
            )


if __name__ == "__main__":
    unittest.main()
