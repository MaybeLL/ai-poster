import json
import unittest
from datetime import datetime, timezone

from app.core.content_job import ContentJob, JobEvent
from app.db.adapters import (
    document_to_model,
    draft_to_model,
    event_to_model,
    job_to_model,
    model_to_document,
    model_to_draft,
    model_to_job,
    model_to_packet,
    model_to_qa_review,
    packet_to_model,
    qa_review_to_model,
)
from app.db.models import (
    ContentJobModel,
    DraftPackageModel,
    JobEventModel,
    QaReviewModel,
    RawDocumentModel,
    ResearchPacketModel,
)
from app.services.ingestion.rss_adapter import RawDocument
from app.services.qa.service import QaReviewResult
from app.services.research.service import ResearchPacket, SourceBrief, TimelineEntry
from app.services.writing.service import DraftArticle, DraftPackage


class AdapterRoundTripTest(unittest.TestCase):
    def test_raw_document_round_trip(self) -> None:
        doc = RawDocument(
            source_id="openai-blog",
            title="GPT-5 Released",
            url="https://example.com/gpt5",
            summary="A new model.",
            published_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
            authority_weight=10,
        )
        model = document_to_model(doc)
        result = model_to_document(model)
        self.assertEqual(result.source_id, doc.source_id)
        self.assertEqual(result.title, doc.title)
        self.assertEqual(result.url, doc.url)
        self.assertEqual(result.summary, doc.summary)
        self.assertEqual(result.published_at, doc.published_at)
        self.assertEqual(result.authority_weight, doc.authority_weight)

    def test_raw_document_with_none_published_at(self) -> None:
        doc = RawDocument(
            source_id="src",
            title="T",
            url="https://a.com",
            summary="",
            published_at=None,
            authority_weight=1,
        )
        model = document_to_model(doc)
        result = model_to_document(model)
        self.assertIsNone(result.published_at)

    def test_job_event_round_trip(self) -> None:
        now = datetime.now(timezone.utc)
        event = JobEvent(
            from_status="created",
            to_status="ingested",
            reason="ingested",
            created_at=now,
            rewind=False,
        )
        model = event_to_model(event, "job-1")
        self.assertEqual(model.job_id, "job-1")
        self.assertEqual(model.from_status, "created")
        self.assertEqual(model.to_status, "ingested")
        self.assertEqual(model.rewind, False)

    def test_content_job_to_model(self) -> None:
        job = ContentJob(job_id="j1", topic="test")
        model = job_to_model(job)
        self.assertEqual(model.job_id, "j1")
        self.assertEqual(model.topic, "test")
        self.assertEqual(model.status, "created")

    def test_model_to_content_job(self) -> None:
        model = ContentJobModel(job_id="j1", topic="test", status="ingested")
        job = model_to_job(model)
        self.assertEqual(job.job_id, "j1")
        self.assertEqual(job.topic, "test")
        self.assertEqual(job.status, "ingested")

    def test_research_packet_round_trip(self) -> None:
        packet = ResearchPacket(
            cluster_id="c1",
            headline="Test",
            event_summary="summary",
            primary_source_summary="primary",
            source_briefs=[
                SourceBrief(
                    source_id="s1",
                    title="t1",
                    url="https://x.com",
                    summary="s",
                    published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
                    authority_weight=10,
                )
            ],
            timeline=[
                TimelineEntry(
                    source_id="s1",
                    title="t1",
                    published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
                )
            ],
            keywords=["AI"],
            open_questions=["q1"],
        )
        model = packet_to_model(packet, "job-1")
        self.assertEqual(model.job_id, "job-1")
        result = model_to_packet(model)
        self.assertEqual(result.cluster_id, packet.cluster_id)
        self.assertEqual(result.headline, packet.headline)
        self.assertEqual(result.event_summary, packet.event_summary)
        self.assertEqual(result.keywords, packet.keywords)
        self.assertEqual(result.open_questions, packet.open_questions)
        self.assertEqual(len(result.source_briefs), 1)
        self.assertEqual(result.source_briefs[0].source_id, "s1")

    def test_draft_package_round_trip(self) -> None:
        draft = DraftPackage(
            long_article=DraftArticle(cluster_id="c1", title="Long", body="Long body"),
            short_post=DraftArticle(cluster_id="c1", title="Short", body="Short body"),
        )
        model = draft_to_model(draft, "job-1")
        self.assertEqual(model.job_id, "job-1")
        result = model_to_draft(model)
        self.assertEqual(result.long_article.title, "Long")
        self.assertEqual(result.short_post.title, "Short")

    def test_qa_review_round_trip(self) -> None:
        review = QaReviewResult(
            total_score=85,
            factual_accuracy_score=90,
            viewpoint_clarity_score=80,
            sources_verified=True,
            within_time_window=True,
            claims_supported=True,
            long_short_consistent=True,
            failed_checks=[],
        )
        model = qa_review_to_model(review, "job-1", True)
        self.assertTrue(model.accepted)
        result_review, accepted = model_to_qa_review(model)
        self.assertEqual(result_review.total_score, 85)
        self.assertTrue(accepted)


if __name__ == "__main__":
    unittest.main()
