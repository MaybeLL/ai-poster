import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import AppSettings
from app.main import build_ingestion_summary, build_pipeline_summary


class IngestionFailureHandlingTest(unittest.TestCase):
    def test_ingestion_summary_reports_source_errors_without_crashing(self) -> None:
        payload = {
            "sources": [
                {
                    "source_id": "broken-source",
                    "name": "Broken Source",
                    "kind": "rss",
                    "url": "https://broken.example/rss.xml",
                    "enabled": True,
                    "authority_weight": 10,
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "sources.json").write_text(json.dumps(payload), encoding="utf-8")
            settings = AppSettings(environment="test", data_dir=data_dir)

            summary = build_ingestion_summary(
                settings=settings,
                now=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
                lookback_hours=24,
                fetcher=self._raise_fetch_error,
            )

        self.assertIn("error_count: 1", summary)
        self.assertIn("document_count: 0", summary)

    def test_pipeline_summary_rejects_when_no_packets_can_be_built(self) -> None:
        payload = {
            "sources": [
                {
                    "source_id": "broken-source",
                    "name": "Broken Source",
                    "kind": "rss",
                    "url": "https://broken.example/rss.xml",
                    "enabled": True,
                    "authority_weight": 10,
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "sources.json").write_text(json.dumps(payload), encoding="utf-8")
            settings = AppSettings(environment="test", data_dir=data_dir)

            summary = build_pipeline_summary(
                settings=settings,
                now=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
                lookback_hours=24,
                limit=1,
                fetcher=self._raise_fetch_error,
            )

        self.assertIn("final_status: rejected", summary)
        self.assertIn("error_count: 1", summary)

    @staticmethod
    def _raise_fetch_error(url: str) -> str:
        raise RuntimeError(f"failed to fetch: {url}")


if __name__ == "__main__":
    unittest.main()
