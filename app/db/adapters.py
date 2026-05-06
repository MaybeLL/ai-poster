from __future__ import annotations

import json

from app.core.content_job import ContentJob, JobEvent
from app.db.models import (
    ContentJobModel,
    DraftPackageModel,
    EventClusterModel,
    IngestionRunModel,
    JobEventModel,
    QaReviewModel,
    RawDocumentModel,
    ResearchPacketModel,
)
from app.services.events.engine import EventCluster
from app.services.ingestion.rss_adapter import RawDocument
from app.services.ingestion.service import IngestionResult, SourceIngestionError
from app.services.qa.service import QaReviewResult
from app.services.research.service import ResearchPacket
from app.services.writing.service import DraftPackage


def job_to_model(job: ContentJob) -> ContentJobModel:
    return ContentJobModel(
        job_id=job.job_id,
        topic=job.topic,
        status=job.status,
    )


def model_to_job(model: ContentJobModel) -> ContentJob:
    job = ContentJob(job_id=model.job_id, topic=model.topic)
    job.status = model.status
    job.events = [event_model_to_event(e) for e in (model.events or [])]
    return job


def event_to_model(event: JobEvent, job_id: str) -> JobEventModel:
    return JobEventModel(
        job_id=job_id,
        from_status=event.from_status,
        to_status=event.to_status,
        reason=event.reason,
        created_at=event.created_at,
        rewind=event.rewind,
    )


def event_model_to_event(model: JobEventModel) -> JobEvent:
    return JobEvent(
        from_status=model.from_status,
        to_status=model.to_status,
        reason=model.reason,
        created_at=model.created_at,
        rewind=model.rewind,
    )


def document_to_model(document: RawDocument, ingestion_run_id: str | None = None) -> RawDocumentModel:
    return RawDocumentModel(
        source_id=document.source_id,
        title=document.title,
        url=document.url,
        summary=document.summary,
        published_at=document.published_at,
        authority_weight=document.authority_weight,
        ingestion_run_id=ingestion_run_id,
    )


def model_to_document(model: RawDocumentModel) -> RawDocument:
    return RawDocument(
        source_id=model.source_id,
        title=model.title,
        url=model.url,
        summary=model.summary,
        published_at=model.published_at,
        authority_weight=model.authority_weight,
    )


def cluster_to_model(cluster: EventCluster) -> EventClusterModel:
    return EventClusterModel(
        cluster_id=cluster.cluster_id,
        headline=cluster.headline,
        document_count=cluster.document_count,
        freshness_score=cluster.score.freshness_score,
        authority_score=cluster.score.authority_score,
        coverage_score=cluster.score.coverage_score,
        total_score=cluster.score.total_score,
    )


def model_to_cluster(model: EventClusterModel) -> EventCluster:
    from app.services.events.engine import EventScore

    documents = [model_to_document(link.document) for link in (model.document_links or [])]
    return EventCluster(
        cluster_id=model.cluster_id,
        headline=model.headline,
        documents=documents,
        score=EventScore(
            freshness_score=model.freshness_score,
            authority_score=model.authority_score,
            coverage_score=model.coverage_score,
            total_score=model.total_score,
        ),
    )


def packet_to_model(packet: ResearchPacket, job_id: str) -> ResearchPacketModel:
    return ResearchPacketModel(
        job_id=job_id,
        cluster_id=packet.cluster_id,
        headline=packet.headline,
        event_summary=packet.event_summary,
        primary_source_summary=packet.primary_source_summary,
        source_briefs_json=json.dumps([b.to_dict() for b in packet.source_briefs]),
        timeline_json=json.dumps([t.to_dict() for t in packet.timeline]),
        keywords_json=json.dumps(packet.keywords),
        open_questions_json=json.dumps(packet.open_questions),
    )


def model_to_packet(model: ResearchPacketModel) -> ResearchPacket:
    from app.services.research.service import SourceBrief, TimelineEntry

    source_briefs = [SourceBrief.from_dict(b) for b in json.loads(model.source_briefs_json)]
    timeline = [TimelineEntry.from_dict(t) for t in json.loads(model.timeline_json)]
    return ResearchPacket(
        cluster_id=model.cluster_id,
        headline=model.headline,
        event_summary=model.event_summary,
        primary_source_summary=model.primary_source_summary,
        source_briefs=source_briefs,
        timeline=timeline,
        keywords=json.loads(model.keywords_json),
        open_questions=json.loads(model.open_questions_json),
    )


def draft_to_model(draft: DraftPackage, job_id: str) -> DraftPackageModel:
    return DraftPackageModel(
        job_id=job_id,
        cluster_id=draft.long_article.cluster_id,
        long_title=draft.long_article.title,
        long_body=draft.long_article.body,
        short_title=draft.short_post.title,
        short_body=draft.short_post.body,
    )


def model_to_draft(model: DraftPackageModel) -> DraftPackage:
    from app.services.writing.service import DraftArticle

    return DraftPackage(
        long_article=DraftArticle(
            cluster_id=model.cluster_id,
            title=model.long_title,
            body=model.long_body,
        ),
        short_post=DraftArticle(
            cluster_id=model.cluster_id,
            title=model.short_title,
            body=model.short_body,
        ),
    )


def qa_review_to_model(review: QaReviewResult, job_id: str, accepted: bool) -> QaReviewModel:
    return QaReviewModel(
        job_id=job_id,
        total_score=review.total_score,
        factual_accuracy_score=review.factual_accuracy_score,
        viewpoint_clarity_score=review.viewpoint_clarity_score,
        sources_verified=review.sources_verified,
        within_time_window=review.within_time_window,
        claims_supported=review.claims_supported,
        long_short_consistent=review.long_short_consistent,
        failed_checks_json=json.dumps(review.failed_checks),
        accepted=accepted,
    )


def model_to_qa_review(model: QaReviewModel) -> tuple[QaReviewResult, bool]:
    review = QaReviewResult(
        total_score=model.total_score,
        factual_accuracy_score=model.factual_accuracy_score,
        viewpoint_clarity_score=model.viewpoint_clarity_score,
        sources_verified=model.sources_verified,
        within_time_window=model.within_time_window,
        claims_supported=model.claims_supported,
        long_short_consistent=model.long_short_consistent,
        failed_checks=json.loads(model.failed_checks_json),
    )
    return review, model.accepted


def ingestion_result_to_run_model(result: IngestionResult, run_id: str, lookback_hours: int) -> IngestionRunModel:
    return IngestionRunModel(
        run_id=run_id,
        lookback_hours=lookback_hours,
        document_count=len(result.documents),
        error_count=len(result.source_errors),
        source_errors_json=json.dumps([e.to_dict() for e in result.source_errors]),
    )
