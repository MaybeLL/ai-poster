import json
import unittest

from app.agents.provider import AgentProvider, AgentRequest, AgentResponse
from app.services.qa.service import AgentQaService, QaService
from app.services.research.service import ResearchPacket, SourceBrief, TimelineEntry
from app.services.writing.service import DraftArticle, DraftPackage


class FakeProvider(AgentProvider):
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.requests: list[AgentRequest] = []

    def generate(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return AgentResponse(provider_name="fake", output_text=self.output_text)


class AgentQaServiceTest(unittest.TestCase):
    def test_review_package_uses_agent_scores_when_valid(self) -> None:
        packet = ResearchPacket(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            event_summary="summary",
            primary_source_summary="Official launch post with product details.",
            source_briefs=[
                SourceBrief(
                    source_id="openai-blog",
                    title="OpenAI launches Codex Cloud",
                    url="https://example.com/openai",
                    summary="Official launch post with product details.",
                    published_at=None,
                    authority_weight=10,
                )
            ],
            timeline=[TimelineEntry(source_id="openai-blog", title="OpenAI launches Codex Cloud", published_at=None)],
            keywords=["OpenAI"],
            open_questions=[],
        )
        package = DraftPackage(
            long_article=DraftArticle(cluster_id="cluster-1", title="Long", body="Long body"),
            short_post=DraftArticle(cluster_id="cluster-1", title="Short", body="Short body"),
        )
        provider = FakeProvider(
            json.dumps(
                {
                    "total_score": 88,
                    "factual_accuracy_score": 94,
                    "viewpoint_clarity_score": 82,
                    "sources_verified": True,
                    "within_time_window": True,
                    "claims_supported": True,
                    "long_short_consistent": True,
                    "failed_checks": [],
                }
            )
        )

        result = AgentQaService(provider=provider).review_package(packet=packet, draft_package=package)

        self.assertEqual(result.total_score, 88)
        self.assertTrue(result.claims_supported)
        self.assertEqual(provider.requests[0].task_name, "review")

    def test_review_package_falls_back_when_agent_output_is_invalid(self) -> None:
        packet = ResearchPacket(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            event_summary="summary",
            primary_source_summary="Official launch post with product details.",
            source_briefs=[],
            timeline=[],
            keywords=["OpenAI"],
            open_questions=[],
        )
        package = DraftPackage(
            long_article=DraftArticle(cluster_id="cluster-1", title="Long", body="Long body"),
            short_post=DraftArticle(cluster_id="cluster-1", title="Different topic", body="Short body"),
        )
        provider = FakeProvider("not-json")

        result = AgentQaService(provider=provider, fallback=QaService()).review_package(packet=packet, draft_package=package)

        self.assertFalse(result.long_short_consistent)


if __name__ == "__main__":
    unittest.main()
