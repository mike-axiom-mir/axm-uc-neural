import unittest

from neural.axm_brain import (
    AXMBrain,
    AXM_ROOTS,
    BrainConfig,
    ContinuitySpine,
    Experience,
    RootEvidence,
    RootReview,
)
from neural.axm_brain.state import snapshot_payload


def pass_review():
    return RootReview(
        RootEvidence(
            root,
            "PASS",
            f"fixture evidence for {root}",
            evidence_refs=(f"fixture:{root}",),
        )
        for root in AXM_ROOTS
    )


class RootsAndContinuityTests(unittest.TestCase):
    def brain(self):
        return AXMBrain(
            BrainConfig(
                input_size=2,
                hidden_size=4,
                output_size=1,
                seed=31,
                replay_capacity=8,
            )
        )

    def test_roots_are_embedded_in_brain_snapshot(self):
        brain = self.brain()
        snapshot = brain.to_snapshot()
        self.assertEqual(
            tuple(
                item["name"]
                for item
                in snapshot["body"]["roots"]["contract"]["roots"]
            ),
            AXM_ROOTS,
        )
        restored = AXMBrain.from_snapshot(snapshot)
        self.assertEqual(
            restored.to_snapshot(),
            snapshot,
        )

    def test_validly_rehashed_wrong_roots_are_rejected(self):
        brain = self.brain()
        body = brain.to_snapshot()["body"]
        body["roots"]["contract"]["roots"][0]["name"] = "NOT_TRUTH"
        forged = snapshot_payload(body)
        with self.assertRaises(ValueError):
            AXMBrain.from_snapshot(forged)

    def test_root_review_needs_all_four_roots(self):
        with self.assertRaises(ValueError):
            RootReview(
                (
                    RootEvidence(
                        "TRUTH",
                        "PASS",
                        "only one",
                    ),
                )
            )

    def test_unknown_root_evidence_holds_transition(self):
        evidence = []
        for root in AXM_ROOTS:
            evidence.append(
                RootEvidence(
                    root,
                    "UNKNOWN" if root == "AGENCY" else "PASS",
                    f"fixture {root}",
                )
            )
        review = RootReview(evidence)
        self.assertFalse(review.passed)
        self.assertEqual(
            review.held_roots,
            ("AGENCY",),
        )

    def test_preserve_probe_passes_original_state(self):
        brain = self.brain()
        snapshot = brain.to_snapshot()
        probe = ContinuitySpine.capture(
            "birth-behavior",
            snapshot,
            (
                (0.1, 0.2),
                (0.3, -0.4),
            ),
            tolerance=0.0,
        )
        spine = ContinuitySpine((probe,))
        result = spine.evaluate(snapshot)
        self.assertTrue(result["passed"])

    def test_learning_can_trigger_continuity_regression(self):
        brain = self.brain()
        before = brain.to_snapshot()
        probe = ContinuitySpine.capture(
            "preserve-response",
            before,
            ((1.0, -1.0),),
            tolerance=1e-12,
        )
        spine = ContinuitySpine((probe,))
        for _ in range(60):
            brain.experience(
                Experience(
                    [1.0, -1.0],
                    target=[1.0],
                ),
                remember=False,
            )
            brain.hidden = [
                0.0
            ] * brain.config.hidden_size
        after = brain.to_snapshot()
        result = spine.evaluate(after)
        self.assertFalse(result["passed"])
        self.assertEqual(
            result["results"][0]["status"],
            "REGRESSION",
        )

    def test_supersede_keeps_provenance_but_stops_blocking(self):
        brain = self.brain()
        before = brain.to_snapshot()
        old_probe = ContinuitySpine.capture(
            "old-response",
            before,
            ((0.5, 0.5),),
            tolerance=0.0,
        )
        new_probe = ContinuitySpine.capture(
            "new-response",
            before,
            ((-0.5, -0.5),),
            tolerance=0.0,
        )
        spine = ContinuitySpine(
            (old_probe, new_probe)
        )
        spine.set_disposition(
            "old-response",
            "SUPERSEDE",
            reason="new probe explicitly replaces old behavior",
            replacement_probe_id="new-response",
        )
        report = spine.evaluate(before)
        self.assertTrue(report["passed"])
        old = next(
            item
            for item in report["results"]
            if item["probe_id"] == "old-response"
        )
        self.assertEqual(
            old["status"],
            "NON_BLOCKING",
        )

    def test_forget_requires_reason_and_is_non_blocking(self):
        brain = self.brain()
        snapshot = brain.to_snapshot()
        probe = ContinuitySpine.capture(
            "obsolete",
            snapshot,
            ((0.0, 0.0),),
        )
        spine = ContinuitySpine((probe,))
        spine.set_disposition(
            "obsolete",
            "FORGET",
            reason="behavior was explicitly retired",
        )
        self.assertTrue(
            spine.evaluate(snapshot)["passed"]
        )

    def test_transition_gate_accepts_only_roots_and_continuity(self):
        brain = self.brain()
        before = brain.to_snapshot()
        probe = ContinuitySpine.capture(
            "stable",
            before,
            ((0.0, 0.0),),
            tolerance=1.0,
        )
        spine = ContinuitySpine((probe,))
        brain.experience(
            Experience(
                [0.2, 0.1],
                target=[0.1],
                directions=("LEARN",),
            )
        )
        candidate = brain.to_snapshot()
        report = spine.review_transition(
            before,
            candidate,
            pass_review(),
        )
        self.assertEqual(
            report["decision"],
            "ACCEPT",
        )
        self.assertGreater(
            report["state_delta"]["changed_parameters"],
            0,
        )

    def test_continuity_spine_snapshot_roundtrip(self):
        brain = self.brain()
        snapshot = brain.to_snapshot()
        probe = ContinuitySpine.capture(
            "roundtrip",
            snapshot,
            ((0.25, -0.25),),
        )
        spine = ContinuitySpine((probe,))
        restored = ContinuitySpine.from_snapshot(
            spine.to_snapshot()
        )
        self.assertEqual(
            restored.to_snapshot(),
            spine.to_snapshot(),
        )


if __name__ == "__main__":
    unittest.main()
