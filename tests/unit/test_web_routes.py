import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.settings import AppSettings
from app.db.models import Base
from app.web import state
from app.web.app import create_app

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>OpenAI releases GPT-5</title>
      <link>https://example.com/gpt5</link>
      <description>GPT-5 announced.</description>
      <pubDate>Mon, 05 May 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


class WebRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(cls._tmpdir.name) / "test.db"
        cls.settings = AppSettings(
            environment="test",
            data_dir=Path("data"),
            database_url=f"sqlite:///{db_path}",
        )
        cls.app = create_app(settings=cls.settings)
        Base.metadata.create_all(state.get_engine())
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls) -> None:
        Base.metadata.drop_all(state.get_engine())
        cls._tmpdir.cleanup()

    def test_health(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("backend", data)

    def test_list_jobs_empty(self) -> None:
        response = self.client.get("/api/v1/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_job_not_found(self) -> None:
        response = self.client.get("/api/v1/jobs/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_get_job_events_not_found(self) -> None:
        response = self.client.get("/api/v1/jobs/nonexistent/events")
        self.assertEqual(response.status_code, 404)

    def test_get_job_research_not_found(self) -> None:
        response = self.client.get("/api/v1/jobs/nonexistent/research")
        self.assertEqual(response.status_code, 404)

    def test_get_job_draft_not_found(self) -> None:
        response = self.client.get("/api/v1/jobs/nonexistent/draft")
        self.assertEqual(response.status_code, 404)

    def test_get_job_qa_not_found(self) -> None:
        response = self.client.get("/api/v1/jobs/nonexistent/qa")
        self.assertEqual(response.status_code, 404)

    def test_list_runs_empty(self) -> None:
        response = self.client.get("/api/v1/runs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_run_not_found(self) -> None:
        response = self.client.get("/api/v1/runs/nonexistent")
        self.assertEqual(response.status_code, 404)

    @patch("app.services.ingestion.service.IngestionService._default_fetcher")
    def test_trigger_ingest(self, mock_fetcher) -> None:
        mock_fetcher.return_value = RSS_XML
        response = self.client.post("/api/v1/runs/ingest?lookback_hours=24")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("run_id", data)

    @patch("app.services.ingestion.service.IngestionService._default_fetcher")
    def test_trigger_pipeline(self, mock_fetcher) -> None:
        mock_fetcher.return_value = RSS_XML
        response = self.client.post("/api/v1/runs/pipeline?lookback_hours=24&limit=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("job_ids", data)


if __name__ == "__main__":
    unittest.main()
