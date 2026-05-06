import unittest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.content_job import ContentJob
from app.core.quality_gate import QualityDecision, QualityGate
from app.db.adapters import model_to_job
from app.db.models import Base
from app.db.repository import (
    get_job_by_id,
    get_research_packet,
    list_jobs,
    save_content_job,
    save_draft_package,
    save_job_events,
    save_qa_review,
    save_research_packet,
)
from app.services.qa.service import QaReviewResult
from app.services.research.service import ResearchPacket, SourceBrief, TimelineEntry
from app.services.writing.service import DraftArticle, DraftPackage


class RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def _make_job(self, job_id: str = "job-1", topic: str = "Test topic") -> ContentJob:
        job = ContentJob(job_id=job_id, topic=topic)
        job.transition_to("ingested", reason="ingested")
        return job

    def _make_packet(self) -> ResearchPacket:
        return ResearchPacket(
            cluster_id="c1",
            headline="Test headline",
            event_summary="Event summary",
            primary_source_summary="Primary summary",
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

    def _make_draft(self) -> DraftPackage:
        return DraftPackage(
            long_article=DraftArticle(cluster_id="c1", title="Long", body="Long body"),
            short_post=DraftArticle(cluster_id="c1", title="Short", body="Short body"),
        )

    def _make_review(self) -> QaReviewResult:
        return QaReviewResult(
            total_score=88,
            factual_accuracy_score=92,
            viewpoint_clarity_score=82,
            sources_verified=True,
            within_time_window=True,
            claims_supported=True,
            long_short_consistent=True,
            failed_checks=[],
        )

    def test_save_and_retrieve_job(self) -> None:
        job = self._make_job()
        save_content_job(self.session, job)
        save_job_events(self.session, job)
        self.session.commit()

        retrieved = get_job_by_id(self.session, job.job_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.job_id, job.job_id)
        self.assertEqual(retrieved.status, job.status)
        self.assertEqual(len(retrieved.events), len(job.events))

    def test_list_jobs(self) -> None:
        for i in range(3):
            job = self._make_job(job_id=f"job-{i}", topic=f"Topic {i}")
            save_content_job(self.session, job)
        self.session.commit()

        jobs = list_jobs(self.session)
        self.assertEqual(len(jobs), 3)

    def test_list_jobs_filter_by_status(self) -> None:
        job1 = self._make_job(job_id="job-a")
        job2 = self._make_job(job_id="job-b")
        job2.transition_to("normalized", reason="next")
        save_content_job(self.session, job1)
        save_content_job(self.session, job2)
        self.session.commit()

        ingested_jobs = list_jobs(self.session, status="ingested")
        self.assertEqual(len(ingested_jobs), 1)
        self.assertEqual(ingested_jobs[0].job_id, "job-a")

    def test_save_and_retrieve_research_packet(self) -> None:
        job = self._make_job()
        save_content_job(self.session, job)
        packet = self._make_packet()
        save_research_packet(self.session, packet, job.job_id)
        self.session.commit()

        retrieved = get_research_packet(self.session, job.job_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.headline, packet.headline)
        self.assertEqual(retrieved.keywords, packet.keywords)

    def test_save_draft_package(self) -> None:
        job = self._make_job()
        save_content_job(self.session, job)
        draft = self._make_draft()
        save_draft_package(self.session, draft, job.job_id)
        self.session.commit()

    def test_save_qa_review(self) -> None:
        job = self._make_job()
        save_content_job(self.session, job)
        review = self._make_review()
        decision = QualityGate().evaluate(review.to_quality_gate_input())
        save_qa_review(self.session, review, decision, job.job_id)
        self.session.commit()


if __name__ == "__main__":
    unittest.main()
