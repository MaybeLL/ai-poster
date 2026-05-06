import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import AppSettings
from app.main import build_event_summary


class EventCliSummaryTest(unittest.TestCase):
    def test_build_event_summary_reports_top_clusters(self) -> None:
        feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OpenAI Blog</title>
    <item>
      <title>OpenAI launches Codex Cloud</title>
      <link>https://example.com/codex-cloud</link>
      <pubDate>Tue, 28 Apr 2026 10:00:00 +0000</pubDate>
      <description>Official launch post.</description>
    </item>
    <item>
      <title>OpenAI launches Codex Cloud for developers</title>
      <link>https://example.com/codex-cloud-coverage</link>
      <pubDate>Tue, 28 Apr 2026 09:00:00 +0000</pubDate>
      <description>Coverage of the same release.</description>
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

            summary = build_event_summary(
                settings=settings,
                now=datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc),
                lookback_hours=24,
                limit=3,
                fetcher=lambda url: feed_xml,
            )

        self.assertIn("cluster_count: 1", summary)
        self.assertIn("OpenAI launches Codex Cloud", summary)


if __name__ == "__main__":
    unittest.main()
