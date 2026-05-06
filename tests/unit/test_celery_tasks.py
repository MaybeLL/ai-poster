import os
import unittest
from pathlib import Path


@unittest.skipUnless(
    os.environ.get("AI_POSTER_CELERY_TESTS"),
    "Set AI_POSTER_CELERY_TESTS=1 to run Celery task tests (requires Redis)",
)
class CeleryTaskTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["AI_POSTER_ENV"] = "test"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    def test_celery_app_loads(self) -> None:
        from app.tasks.celery_app import celery_app

        self.assertEqual(celery_app.main, "ai_poster")
        self.assertIn("daily-pipeline-run", celery_app.conf.beat_schedule)

    def test_ingest_sources_task_runs_eager(self) -> None:
        os.environ["AI_POSTER_CELERY_BROKER_URL"] = "memory://"
        os.environ["AI_POSTER_CELERY_RESULT_BACKEND"] = "cache+memory://"

        from app.tasks.celery_app import celery_app
        celery_app.conf.task_always_eager = True

        from app.tasks.pipeline_tasks import ingest_sources_task

        result = ingest_sources_task.delay(lookback_hours=24)
        self.assertIn("document_count", result.result)

    def test_run_full_pipeline_task_runs_eager(self) -> None:
        os.environ["AI_POSTER_CELERY_BROKER_URL"] = "memory://"
        os.environ["AI_POSTER_CELERY_RESULT_BACKEND"] = "cache+memory://"

        from app.tasks.celery_app import celery_app
        celery_app.conf.task_always_eager = True
        celery_app.conf.broker_url = "memory://"

        from app.tasks.pipeline_tasks import run_full_pipeline_task

        result = run_full_pipeline_task.delay(lookback_hours=24, limit=1)
        self.assertIn("ingest_run_id", result.result)
        self.assertIn("job_ids", result.result)


if __name__ == "__main__":
    unittest.main()
