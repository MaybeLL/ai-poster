import unittest

from app.core.quality_gate import QualityGateInput
from app.workflows.mvp_workflow import MvpWorkflowRunner


class MvpWorkflowRunnerTest(unittest.TestCase):
    def test_run_accepts_job_when_quality_gate_passes(self) -> None:
        runner = MvpWorkflowRunner()

        result = runner.run(
            topic="OpenAI launches a new enterprise agent capability",
            qa_input=QualityGateInput(
                total_score=85,
                factual_accuracy_score=94,
                viewpoint_clarity_score=81,
                sources_verified=True,
                within_time_window=True,
                claims_supported=True,
                long_short_consistent=True,
            ),
        )

        self.assertEqual(result.job.status, "accepted")
        self.assertTrue(result.decision.accepted)
        self.assertEqual(result.completed_stages[-1], "accepted")

    def test_run_rejects_job_when_quality_gate_fails(self) -> None:
        runner = MvpWorkflowRunner()

        result = runner.run(
            topic="Speculative rumor without reliable sourcing",
            qa_input=QualityGateInput(
                total_score=83,
                factual_accuracy_score=95,
                viewpoint_clarity_score=84,
                sources_verified=False,
                within_time_window=True,
                claims_supported=True,
                long_short_consistent=True,
            ),
        )

        self.assertEqual(result.job.status, "rejected")
        self.assertFalse(result.decision.accepted)
        self.assertIn("sources_verified", result.decision.failed_checks)
        self.assertEqual(result.completed_stages[-1], "rejected")


if __name__ == "__main__":
    unittest.main()
