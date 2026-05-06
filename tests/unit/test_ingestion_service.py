import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import AppSettings
from app.services.ingestion.service import IngestionService


class IngestionServiceTest(unittest.TestCase):
    def test_ingest_recent_documents_reads_catalog_and_aggregates_documents(self) -> None:
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OpenAI Blog</title>
    <item>
      <title>Recent release</title>
      <link>https://example.com/recent</link>
      <pubDate>Tue, 28 Apr 2026 10:00:00 +0000</pubDate>
      <description>Recent item body.</description>
    </item>
  </channel>
</rss>
"""
        payload = {
            "sources": [
                {
                    "source_id": "openai-blog",
                    "name": "OpenAI Blog",
                    "kind": "rss",
                    "url": "https://example.com/rss.xml",
                    "enabled": True,
                    "authority_weight": 10,
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "sources.json").write_text(json.dumps(payload), encoding="utf-8")
            settings = AppSettings(environment="test", data_dir=data_dir)
            service = IngestionService(settings=settings, fetcher=lambda url: feed_xml)

            documents = service.ingest_recent_documents(
                now=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
                lookback_hours=24,
            )

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].source_id, "openai-blog")
        self.assertEqual(documents[0].title, "Recent release")

    def test_ingest_recent_documents_rejects_unsupported_source_kind(self) -> None:
        payload = {
            "sources": [
                {
                    "source_id": "unsupported",
                    "name": "Unsupported",
                    "kind": "html",
                    "url": "https://example.com",
                    "enabled": True,
                    "authority_weight": 1,
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "sources.json").write_text(json.dumps(payload), encoding="utf-8")
            settings = AppSettings(environment="test", data_dir=data_dir)
            service = IngestionService(settings=settings, fetcher=lambda url: "")

            with self.assertRaises(ValueError):
                service.ingest_recent_documents(
                    now=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
                    lookback_hours=24,
                )


if __name__ == "__main__":
    unittest.main()
