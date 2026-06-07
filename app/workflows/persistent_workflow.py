from __future__ import annotations

import logging
from uuid import uuid4

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.content_job import ContentJob
from app.core.quality_gate import QualityDecision, QualityGate
from app.db.repository import (
    save_content_job,
    save_draft_package,
    save_event_clusters,
    save_ingestion_result,
    save_job_events,
    save_posts,
    save_qa_review,
    save_research_packet,
)
from app.posting.publishers import Publisher
from app.posting.writer import write_post
from app.services.events.engine import EventCluster
from app.services.factory import ContentServices
from app.services.ingestion.service import IngestionResult
from app.workflows.mvp_workflow import WorkflowRunResult


logger = logging.getLogger(__name__)


class PersistentWorkflowRunner:
    """Runs the full pipeline and persists every step to the database."""

    pipeline_stages = (
        "ingested",
        "normalized",
        "clustered",
        "selected",
        "researched",
        "outlined",
        "drafted",
        "claims_extracted",
        "verified",
        "reviewed",
    )

    def __init__(
        self,
        session: Session,
        content_services: ContentServices,
        quality_gate: QualityGate | None = None,
        output_dir: Path | None = None,
        publishers: list[Publisher] | None = None,
    ) -> None:
        self.session = session
        self.content_services = content_services
        self.quality_gate = quality_gate or QualityGate()
        self.output_dir = output_dir
        self.publishers = publishers or []

    def save_ingestion(self, result: IngestionResult, lookback_hours: int) -> str:
        run_id = str(uuid4())
        save_ingestion_result(self.session, result, run_id, lookback_hours)
        self.session.commit()
        return run_id

    def save_clusters(self, clusters: list[EventCluster]) -> None:
        save_event_clusters(self.session, clusters, {})
        self.session.commit()

    def run_for_cluster(self, cluster: EventCluster, topic: str) -> WorkflowRunResult:
        job = ContentJob(job_id=str(uuid4()), topic=topic)
        job.transition_to("ingested", reason="Documents ingested for cluster")

        save_content_job(self.session, job)

        for stage in self.pipeline_stages[1:]:
            job.transition_to(stage, reason=f"Completed {stage} stage")

        save_job_events(self.session, job)

        packet = self.content_services.research_service.build_packet(cluster)
        save_research_packet(self.session, packet, job.job_id)

        draft_package = self.content_services.writing_service.build_draft_package(packet)
        save_draft_package(self.session, draft_package, job.job_id)

        review = self.content_services.qa_service.review_package(packet, draft_package)
        decision = self.quality_gate.evaluate(review.to_quality_gate_input())
        save_qa_review(self.session, review, decision, job.job_id)

        posts = self.content_services.posting_service.generate_posts(packet, job.job_id)
        save_posts(self.session, posts, job.job_id)
        if self.output_dir is not None:
            for post in posts:
                write_post(post, self.output_dir)
        for post in posts:
            for publisher in self.publishers:
                publisher.publish(post)

        terminal_status = "accepted" if decision.accepted else "rejected"
        job.transition_to(terminal_status, reason="Quality gate decision recorded")

        session_job = ContentJob(job_id=job.job_id, topic=job.topic)
        session_job.status = job.status
        session_job.events = list(job.events)

        self.session.commit()

        completed_stages = [event.to_status for event in job.events]
        return WorkflowRunResult(
            job=session_job,
            decision=decision,
            completed_stages=completed_stages,
        )
