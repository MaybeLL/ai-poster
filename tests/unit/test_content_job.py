import unittest

from app.core.content_job import ContentJob, InvalidTransitionError


class ContentJobTest(unittest.TestCase):
    def test_transition_updates_status_and_records_event(self) -> None:
        job = ContentJob(job_id="job-001", topic="OpenAI product release")

        event = job.transition_to("ingested", reason="Fetched source documents")

        self.assertEqual(job.status, "ingested")
        self.assertEqual(event.from_status, "created")
        self.assertEqual(event.to_status, "ingested")
        self.assertEqual(event.reason, "Fetched source documents")
        self.assertEqual(len(job.events), 1)

    def test_transition_rejects_invalid_state_jump(self) -> None:
        job = ContentJob(job_id="job-002", topic="Anthropic model update")

        with self.assertRaises(InvalidTransitionError):
            job.transition_to("reviewed", reason="Skipped required pipeline stages")

    def test_rewind_reopens_job_from_known_safe_stage(self) -> None:
        job = ContentJob(job_id="job-003", topic="Google Gemini feature launch")

        for status in ("ingested", "normalized", "clustered", "selected", "researched", "outlined", "drafted"):
            job.transition_to(status, reason=f"Reached {status}")

        rewind_event = job.rewind_to("researched", reason="Need to rebuild outline from verified facts")

        self.assertEqual(job.status, "researched")
        self.assertEqual(rewind_event.from_status, "drafted")
        self.assertEqual(rewind_event.to_status, "researched")
        self.assertTrue(rewind_event.rewind)
        self.assertEqual(len(job.events), 8)


if __name__ == "__main__":
    unittest.main()
