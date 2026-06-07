import unittest

from app.core.quality_gate import QualityGate, QualityGateInput


class QualityGateTest(unittest.TestCase):
    def test_accepts_package_when_scores_and_guards_pass(self) -> None:
        gate = QualityGate()
        payload = QualityGateInput(
            total_score=84,
            factual_accuracy_score=95,
            viewpoint_clarity_score=80,
            sources_verified=True,
            within_time_window=True,
            claims_supported=True,
            long_short_consistent=True,
        )

        decision = gate.evaluate(payload)

        self.assertTrue(decision.accepted)
        self.assertEqual(decision.failed_checks, [])

    def test_rejects_when_claims_are_not_supported_even_with_high_scores(self) -> None:
        gate = QualityGate()
        payload = QualityGateInput(
            total_score=96,
            factual_accuracy_score=97,
            viewpoint_clarity_score=92,
            sources_verified=True,
            within_time_window=True,
            claims_supported=False,
            long_short_consistent=True,
        )

        decision = gate.evaluate(payload)

        self.assertFalse(decision.accepted)
        self.assertIn("claims_supported", decision.failed_checks)

    def test_rejects_when_viewpoint_is_too_weak(self) -> None:
        gate = QualityGate()
        payload = QualityGateInput(
            total_score=88,
            factual_accuracy_score=93,
            viewpoint_clarity_score=60,
            sources_verified=True,
            within_time_window=True,
            claims_supported=True,
            long_short_consistent=True,
        )

        decision = gate.evaluate(payload)

        self.assertFalse(decision.accepted)
        self.assertIn("viewpoint_clarity_score", decision.failed_checks)


if __name__ == "__main__":
    unittest.main()
