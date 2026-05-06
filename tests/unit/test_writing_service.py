from datetime import datetime, timezone
import unittest

from app.services.research.service import ResearchPacket, SourceBrief, TimelineEntry
from app.services.writing.service import WritingService


class WritingServiceTest(unittest.TestCase):
    def test_build_draft_package_generates_long_and_short_versions(self) -> None:
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
                    published_at=datetime(2026, 4, 28, 10, 0, tzinfo=timezone.utc),
                    authority_weight=10,
                )
            ],
            timeline=[
                TimelineEntry(
                    source_id="openai-blog",
                    title="OpenAI launches Codex Cloud",
                    published_at=datetime(2026, 4, 28, 10, 0, tzinfo=timezone.utc),
                )
            ],
            keywords=["OpenAI", "Codex"],
            open_questions=[],
        )

        package = WritingService().build_draft_package(packet)

        self.assertIn("OpenAI launches Codex Cloud", package.long_article.title)
        self.assertIn("为什么值得关注", package.long_article.body)
        self.assertIn("一句话判断", package.short_post.body)
        self.assertEqual(package.long_article.cluster_id, "cluster-1")


if __name__ == "__main__":
    unittest.main()
