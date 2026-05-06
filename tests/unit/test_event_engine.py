from datetime import datetime, timedelta, timezone
import unittest

from app.services.events.engine import EventEngine
from app.services.ingestion.rss_adapter import RawDocument


class EventEngineTest(unittest.TestCase):
    def test_cluster_documents_groups_similar_titles_together(self) -> None:
        now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
        documents = [
            RawDocument(
                source_id="openai-blog",
                title="OpenAI launches Codex Cloud",
                url="https://example.com/openai-1",
                summary="Official launch post.",
                published_at=now - timedelta(hours=1),
                authority_weight=10,
            ),
            RawDocument(
                source_id="techcrunch",
                title="OpenAI launches Codex Cloud for developers",
                url="https://example.com/openai-2",
                summary="Coverage of the same release.",
                published_at=now - timedelta(hours=2),
                authority_weight=7,
            ),
        ]

        clusters = EventEngine().cluster_documents(documents)

        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].document_count, 2)

    def test_rank_clusters_prefers_authoritative_and_recent_events(self) -> None:
        now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
        documents = [
            RawDocument(
                source_id="openai-blog",
                title="OpenAI launches Codex Cloud",
                url="https://example.com/openai",
                summary="Official launch post.",
                published_at=now - timedelta(hours=1),
                authority_weight=10,
            ),
            RawDocument(
                source_id="small-blog",
                title="Tiny startup publishes minor update",
                url="https://example.com/startup",
                summary="Minor update coverage.",
                published_at=now - timedelta(hours=10),
                authority_weight=2,
            ),
        ]
        engine = EventEngine()
        clusters = engine.cluster_documents(documents)

        ranked = engine.rank_clusters(clusters, now=now)

        self.assertEqual(ranked[0].headline, "OpenAI launches Codex Cloud")
        self.assertGreater(ranked[0].score.total_score, ranked[1].score.total_score)

    def test_select_top_clusters_returns_requested_count(self) -> None:
        now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
        documents = [
            RawDocument(
                source_id=f"source-{index}",
                title=f"Event {index}",
                url=f"https://example.com/{index}",
                summary="Test item",
                published_at=now - timedelta(hours=index),
                authority_weight=10 - index,
            )
            for index in range(4)
        ]
        engine = EventEngine()

        selected = engine.select_top_clusters(documents, now=now, limit=2)

        self.assertEqual(len(selected), 2)
        self.assertGreaterEqual(selected[0].score.total_score, selected[1].score.total_score)


if __name__ == "__main__":
    unittest.main()
