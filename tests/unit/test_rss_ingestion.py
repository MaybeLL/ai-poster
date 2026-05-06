from datetime import datetime, timedelta, timezone
import unittest

from app.services.ingestion.rss_adapter import RssIngestionAdapter
from app.services.ingestion.source_catalog import SourceDefinition


class RssIngestionAdapterTest(unittest.TestCase):
    def test_fetch_recent_documents_filters_items_older_than_window(self) -> None:
        now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
        recent_pub_date = self._format_rfc2822(now - timedelta(hours=2))
        old_pub_date = self._format_rfc2822(now - timedelta(days=3))
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OpenAI Blog</title>
    <item>
      <title>Recent release</title>
      <link>https://example.com/recent</link>
      <pubDate>{recent_pub_date}</pubDate>
      <description>Recent item body.</description>
    </item>
    <item>
      <title>Old release</title>
      <link>https://example.com/old</link>
      <pubDate>{old_pub_date}</pubDate>
      <description>Old item body.</description>
    </item>
  </channel>
</rss>
"""
        source = SourceDefinition(
            source_id="openai-blog",
            name="OpenAI Blog",
            kind="rss",
            url="https://example.com/rss.xml",
            authority_weight=10,
            enabled=True,
        )

        adapter = RssIngestionAdapter(fetcher=lambda url: xml)

        documents = adapter.fetch_recent_documents(source=source, now=now, lookback_hours=24)

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0].title, "Recent release")
        self.assertEqual(documents[0].source_id, "openai-blog")

    def test_fetch_recent_documents_keeps_item_without_pubdate(self) -> None:
        now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example Feed</title>
    <item>
      <title>No pubdate item</title>
      <link>https://example.com/no-pubdate</link>
      <description>Missing pubDate should still be reviewed downstream.</description>
    </item>
  </channel>
</rss>
"""
        source = SourceDefinition(
            source_id="example-feed",
            name="Example Feed",
            kind="rss",
            url="https://example.com/feed.xml",
            authority_weight=5,
            enabled=True,
        )

        adapter = RssIngestionAdapter(fetcher=lambda url: xml)

        documents = adapter.fetch_recent_documents(source=source, now=now, lookback_hours=24)

        self.assertEqual(len(documents), 1)
        self.assertIsNone(documents[0].published_at)

    @staticmethod
    def _format_rfc2822(value: datetime) -> str:
        return value.strftime("%a, %d %b %Y %H:%M:%S +0000")


if __name__ == "__main__":
    unittest.main()
