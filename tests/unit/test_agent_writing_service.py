import json
import unittest

from app.agents.provider import AgentProvider, AgentRequest, AgentResponse
from app.services.research.service import ResearchPacket, SourceBrief, TimelineEntry
from app.services.writing.service import AgentWritingService, WritingService


class FakeProvider(AgentProvider):
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.requests: list[AgentRequest] = []

    def generate(self, request: AgentRequest) -> AgentResponse:
        self.requests.append(request)
        return AgentResponse(provider_name="fake", output_text=self.output_text)


class AgentWritingServiceTest(unittest.TestCase):
    def test_build_draft_package_uses_agent_output_when_valid(self) -> None:
        packet = ResearchPacket(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            event_summary="OpenAI launches Codex Cloud. Covered by 2 sources in the current event cluster.",
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
            keywords=["OpenAI", "Codex"],
            open_questions=[],
        )
        provider = FakeProvider(
            json.dumps(
                {
                    "long_title": "Agent long title",
                    "long_body": "Long draft body",
                    "short_title": "Agent short title",
                    "short_body": "Short draft body",
                }
            )
        )

        package = AgentWritingService(provider=provider).build_draft_package(packet)

        self.assertEqual(package.long_article.title, "Agent long title")
        self.assertEqual(package.short_post.body, "Short draft body")
        self.assertEqual(provider.requests[0].task_name, "writing")

    def test_build_draft_package_falls_back_when_agent_output_is_invalid(self) -> None:
        packet = ResearchPacket(
            cluster_id="cluster-1",
            headline="OpenAI launches Codex Cloud",
            event_summary="OpenAI launches Codex Cloud. Covered by 2 sources in the current event cluster.",
            primary_source_summary="Official launch post with product details.",
            source_briefs=[],
            timeline=[],
            keywords=["OpenAI", "Codex"],
            open_questions=[],
        )
        provider = FakeProvider("not-json")

        package = AgentWritingService(provider=provider, fallback=WritingService()).build_draft_package(packet)

        self.assertIn("为什么值得关注", package.long_article.title)


if __name__ == "__main__":
    unittest.main()
