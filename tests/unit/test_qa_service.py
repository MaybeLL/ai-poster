from datetime import datetime, timezone
import unittest

from app.services.qa.service import QaService
from app.services.research.service import ResearchPacket, SourceBrief, TimelineEntry
from app.services.writing.service import DraftArticle, DraftPackage


class QaServiceTest(unittest.TestCase):
    def test_review_package_accepts_consistent_drafts(self) -> None:
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
        package = DraftPackage(
            long_article=DraftArticle(
                cluster_id="cluster-1",
                title="OpenAI launches Codex Cloud 值得关注吗",
                body="OpenAI launches Codex Cloud\n为什么值得关注\nOfficial launch post with product details.",
            ),
            short_post=DraftArticle(
                cluster_id="cluster-1",
                title="OpenAI launches Codex Cloud",
                body="一句话判断：OpenAI launches Codex Cloud 值得继续跟踪。",
            ),
        )

        result = QaService().review_package(packet=packet, draft_package=package)

        self.assertTrue(result.claims_supported)
        self.assertTrue(result.long_short_consistent)
        self.assertGreaterEqual(result.total_score, 80)

    def test_review_package_flags_missing_headline_in_short_post(self) -> None:
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
        package = DraftPackage(
            long_article=DraftArticle(
                cluster_id="cluster-1",
                title="OpenAI launches Codex Cloud 值得关注吗",
                body="OpenAI launches Codex Cloud",
            ),
            short_post=DraftArticle(
                cluster_id="cluster-1",
                title="Different topic",
                body="一句话判断：需要继续观察。",
            ),
        )

        result = QaService().review_package(packet=packet, draft_package=package)

        self.assertFalse(result.long_short_consistent)
        self.assertLess(result.total_score, 80)


if __name__ == "__main__":
    unittest.main()
