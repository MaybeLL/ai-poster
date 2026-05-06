import os
import unittest
from datetime import datetime, timezone

from app.agents.factory import build_agent_provider
from app.core.settings import AppSettings
from app.services.events.engine import EventCluster, EventScore
from app.services.factory import build_content_services
from app.services.ingestion.rss_adapter import RawDocument
from app.services.research.service import ResearchPacket


def _make_sample_cluster() -> EventCluster:
    return EventCluster(
        cluster_id="cluster-integration-1",
        headline="OpenAI releases GPT-5 with improved reasoning",
        documents=[
            RawDocument(
                source_id="openai-blog",
                title="OpenAI releases GPT-5 with improved reasoning",
                url="https://openai.com/blog/gpt-5",
                summary="OpenAI announced GPT-5, featuring enhanced reasoning and multimodal capabilities.",
                published_at=datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
                authority_weight=10,
            ),
            RawDocument(
                source_id="anthropic-news",
                title="OpenAI GPT-5 announcement shakes up AI industry",
                url="https://www.anthropic.com/news/gpt-5-reaction",
                summary="Anthropic comments on the GPT-5 release and its implications for AI safety.",
                published_at=datetime(2026, 4, 29, 14, 0, tzinfo=timezone.utc),
                authority_weight=10,
            ),
        ],
        score=EventScore(
            freshness_score=28.0,
            authority_score=50.0,
            coverage_score=8.0,
            total_score=86.0,
        ),
    )


@unittest.skipUnless(
    os.environ.get("AI_POSTER_INTEGRATION_TESTS"),
    "Set AI_POSTER_INTEGRATION_TESTS=1 to run real-agent integration tests",
)
class AgentIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AppSettings.from_env()

    def test_agent_provider_is_configured(self) -> None:
        provider = build_agent_provider(settings=self.settings)
        self.assertIsNotNone(
            provider,
            f"Agent provider should be configured for backend={self.settings.intelligence_backend}",
        )

    def test_research_agent_produces_valid_output(self) -> None:
        services = build_content_services(settings=self.settings)
        cluster = _make_sample_cluster()
        packet = services.research_service.build_packet(cluster)

        self.assertIsInstance(packet, ResearchPacket)
        self.assertIsNotNone(packet.event_summary.strip())
        self.assertNotIn(
            "Covered by", packet.event_summary,
            "Event summary should not be template-generated",
        )
        self.assertGreater(len(packet.keywords), 0)
        self.assertEqual(packet.cluster_id, cluster.cluster_id)

    def test_writing_agent_produces_valid_output(self) -> None:
        services = build_content_services(settings=self.settings)
        cluster = _make_sample_cluster()
        packet = services.research_service.build_packet(cluster)
        draft_package = services.writing_service.build_draft_package(packet)

        self.assertIsNotNone(draft_package.long_article.title.strip())
        self.assertIsNotNone(draft_package.long_article.body.strip())
        self.assertIsNotNone(draft_package.short_post.title.strip())
        self.assertIsNotNone(draft_package.short_post.body.strip())
        self.assertNotIn(
            "这件事为什么值得关注", draft_package.long_article.title,
            "Long title should not be template-generated",
        )
        self.assertNotIn(
            "一句话判断", draft_package.short_post.body,
            "Short post body should not be template-generated",
        )

    def test_qa_agent_produces_valid_output(self) -> None:
        services = build_content_services(settings=self.settings)
        cluster = _make_sample_cluster()
        packet = services.research_service.build_packet(cluster)
        draft_package = services.writing_service.build_draft_package(packet)
        review = services.qa_service.review_package(packet, draft_package)

        self.assertIsInstance(review.total_score, int)
        self.assertGreaterEqual(review.total_score, 0)
        self.assertLessEqual(review.total_score, 100)
        self.assertIsInstance(review.sources_verified, bool)
        self.assertIsInstance(review.claims_supported, bool)

    def test_full_pipeline_produces_coherent_output(self) -> None:
        services = build_content_services(settings=self.settings)
        cluster = _make_sample_cluster()

        packet = services.research_service.build_packet(cluster)
        draft_package = services.writing_service.build_draft_package(packet)
        review = services.qa_service.review_package(packet, draft_package)

        self.assertIn(
            packet.headline,
            draft_package.long_article.body,
            "Long article should reference the headline",
        )
        self.assertGreaterEqual(
            review.factual_accuracy_score, 0,
            "QA should produce a valid factual accuracy score",
        )


if __name__ == "__main__":
    unittest.main()
