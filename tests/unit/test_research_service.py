from datetime import datetime, timedelta, timezone
import unittest

from app.services.events.engine import EventCluster, EventScore
from app.services.ingestion.rss_adapter import RawDocument
from app.services.research.service import ResearchService


class ResearchServiceTest(unittest.TestCase):
    def test_build_packet_collects_sources_timeline_and_summary(self) -> None:
        now = datetime(2026, 4, 28, 12, 0, tzinfo=timezone.utc)
        cluster = EventCluster(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            documents=[
                RawDocument(
                    source_id="openai-blog",
                    title="OpenAI launches Codex Cloud",
                    url="https://example.com/openai",
                    summary="Official launch post with product details.",
                    published_at=now - timedelta(hours=1),
                    authority_weight=10,
                ),
                RawDocument(
                    source_id="techcrunch",
                    title="OpenAI launches Codex Cloud for developers",
                    url="https://example.com/coverage",
                    summary="Coverage emphasizing developer workflow impact.",
                    published_at=now - timedelta(hours=2),
                    authority_weight=7,
                ),
            ],
            score=EventScore(
                freshness_score=28.0,
                authority_score=50.0,
                coverage_score=8.0,
                total_score=86.0,
            ),
        )

        packet = ResearchService().build_packet(cluster)

        self.assertEqual(packet.cluster_id, "cluster-1")
        self.assertEqual(packet.headline, "OpenAI launches Codex Cloud")
        self.assertEqual(len(packet.source_briefs), 2)
        self.assertEqual(packet.timeline[0].source_id, "techcrunch")
        self.assertIn("OpenAI launches Codex Cloud", packet.event_summary)
        self.assertTrue(packet.primary_source_summary.startswith("Official launch post"))

    def test_build_packet_marks_uncertainty_when_only_one_source_exists(self) -> None:
        cluster = EventCluster(
            cluster_id="cluster-2",
            headline="Single-source rumor",
            documents=[
                RawDocument(
                    source_id="single-source",
                    title="Single-source rumor",
                    url="https://example.com/rumor",
                    summary="Only one source reported this.",
                    published_at=None,
                    authority_weight=3,
                )
            ],
            score=EventScore(
                freshness_score=10.0,
                authority_score=15.0,
                coverage_score=4.0,
                total_score=29.0,
            ),
        )

        packet = ResearchService().build_packet(cluster)

        self.assertIn("single_source_only", packet.open_questions)
        self.assertIn("missing_publication_time", packet.open_questions)


if __name__ == "__main__":
    unittest.main()
