import json
import unittest

from app.agents.provider import AgentProvider, AgentRequest, AgentResponse
from app.services.events.engine import EventCluster, EventScore
from app.services.ingestion.rss_adapter import RawDocument
from app.services.qa.service import AgentQaService
from app.services.research.service import AgentResearchService
from app.services.writing.service import AgentWritingService, DraftArticle, DraftPackage


class CapturingProvider(AgentProvider):
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.requests: list[AgentRequest] = []

    def generate(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return AgentResponse(provider_name="fake", output_text=self.output_text)


class AgentRequestSchemaTest(unittest.TestCase):
    def test_research_request_includes_response_schema(self) -> None:
        cluster = EventCluster(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            documents=[
                RawDocument(
                    source_id="openai-blog",
                    title="OpenAI launches Codex Cloud",
                    url="https://example.com/openai",
                    summary="Official launch post with product details.",
                    published_at=None,
                    authority_weight=10,
                )
            ],
            score=EventScore(28.0, 50.0, 4.0, 82.0),
        )
        provider = CapturingProvider(
            json.dumps(
                {
                    "event_summary": "Agent summary",
                    "primary_source_summary": "Agent source summary",
                    "keywords": ["OpenAI"],
                    "open_questions": [],
                }
            )
        )

        AgentResearchService(provider=provider).build_packet(cluster)

        self.assertEqual(provider.requests[0].response_schema["type"], "object")
        self.assertIn("event_summary", provider.requests[0].response_schema["properties"])

    def test_writing_request_includes_response_schema(self) -> None:
        packet = AgentResearchService(provider=CapturingProvider("{}"), fallback=None)
        del packet  # keep test local without reusing packet variable name

        from app.services.research.service import ResearchPacket, SourceBrief, TimelineEntry

        research_packet = ResearchPacket(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            event_summary="summary",
            primary_source_summary="primary",
            source_briefs=[SourceBrief("openai-blog", "title", "url", "summary", None, 10)],
            timeline=[TimelineEntry("openai-blog", "title", None)],
            keywords=["OpenAI"],
            open_questions=[],
        )
        provider = CapturingProvider(
            json.dumps(
                {
                    "long_title": "Long",
                    "long_body": "Body",
                    "short_title": "Short",
                    "short_body": "Body",
                }
            )
        )

        AgentWritingService(provider=provider).build_draft_package(research_packet)

        self.assertEqual(provider.requests[0].response_schema["type"], "object")
        self.assertIn("long_title", provider.requests[0].response_schema["properties"])

    def test_qa_request_includes_response_schema(self) -> None:
        from app.services.research.service import ResearchPacket

        packet = ResearchPacket(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            event_summary="summary",
            primary_source_summary="primary",
            source_briefs=[],
            timeline=[],
            keywords=["OpenAI"],
            open_questions=[],
        )
        draft_package = DraftPackage(
            long_article=DraftArticle(cluster_id="cluster-1", title="Long", body="Body"),
            short_post=DraftArticle(cluster_id="cluster-1", title="Short", body="Body"),
        )
        provider = CapturingProvider(
            json.dumps(
                {
                    "total_score": 80,
                    "factual_accuracy_score": 90,
                    "viewpoint_clarity_score": 80,
                    "sources_verified": True,
                    "within_time_window": True,
                    "claims_supported": True,
                    "long_short_consistent": True,
                    "failed_checks": [],
                }
            )
        )

        AgentQaService(provider=provider).review_package(packet=packet, draft_package=draft_package)

        self.assertEqual(provider.requests[0].response_schema["type"], "object")
        self.assertIn("total_score", provider.requests[0].response_schema["properties"])


if __name__ == "__main__":
    unittest.main()
