import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import AppSettings
from app.main import build_ingestion_summary


class IngestionCliSummaryTest(unittest.TestCase):
    def test_build_ingestion_summary_reports_document_count(self) -> None:
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

            summary = build_ingestion_summary(
                settings=settings,
                now=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
                lookback_hours=24,
                fetcher=lambda url: feed_xml,
            )

        self.assertIn("source_count: 1", summary)
        self.assertIn("document_count: 1", summary)
        self.assertIn("Recent release", summary)


if __name__ == "__main__":
    unittest.main()
