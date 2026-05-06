import json
import unittest
from datetime import datetime, timezone

from app.agents.provider import AgentProvider, AgentRequest, AgentResponse
from app.services.events.engine import EventCluster, EventScore
from app.services.ingestion.rss_adapter import RawDocument
from app.services.research.service import AgentResearchService, ResearchService


class FakeProvider(AgentProvider):
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.requests: list[AgentRequest] = []

    def generate(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return AgentResponse(provider_name="fake", output_text=self.output_text)


class AgentResearchServiceTest(unittest.TestCase):
    def test_build_packet_uses_agent_output_when_valid(self) -> None:
        cluster = EventCluster(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            documents=[
                RawDocument(
                    source_id="openai-blog",
                    title="OpenAI launches Codex Cloud",
                    url="https://example.com/openai",
                    summary="Official launch post with product details.",
                    published_at=datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
                    authority_weight=10,
                )
            ],
            score=EventScore(
                freshness_score=28.0,
                authority_score=50.0,
                coverage_score=4.0,
                total_score=82.0,
            ),
        )
        provider = FakeProvider(
            json.dumps(
                {
                    "event_summary": "Agent summary",
                    "primary_source_summary": "Agent source summary",
                    "keywords": ["OpenAI", "Codex", "Cloud"],
                    "open_questions": ["confirm_pricing"],
                }
            )
        )

        packet = AgentResearchService(provider=provider).build_packet(cluster)

        self.assertEqual(packet.event_summary, "Agent summary")
        self.assertEqual(packet.primary_source_summary, "Agent source summary")
        self.assertEqual(packet.keywords, ["OpenAI", "Codex", "Cloud"])
        self.assertEqual(packet.open_questions, ["confirm_pricing"])
        self.assertEqual(provider.requests[0].task_name, "research")

    def test_build_packet_falls_back_when_agent_output_is_invalid(self) -> None:
        cluster = EventCluster(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            documents=[
                RawDocument(
                    source_id="openai-blog",
                    title="OpenAI launches Codex Cloud",
                    url="https://example.com/openai",
                    summary="Official launch post with product details.",
                    published_at=datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc),
                    authority_weight=10,
                )
            ],
            score=EventScore(
                freshness_score=28.0,
                authority_score=50.0,
                coverage_score=4.0,
                total_score=82.0,
            ),
        )
        provider = FakeProvider("not-json")

        packet = AgentResearchService(provider=provider, fallback=ResearchService()).build_packet(cluster)

        self.assertIn("Covered by 1 source", packet.event_summary)


if __name__ == "__main__":
    unittest.main()
