from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.content_job import ContentJob
from app.posting.models import Post
from app.core.quality_gate import QualityDecision
from app.db.adapters import (
    cluster_to_model,
    document_to_model,
    draft_to_model,
    event_to_model,
    ingestion_result_to_run_model,
    job_to_model,
    model_to_cluster,
    model_to_document,
    model_to_draft,
    model_to_job,
    model_to_packet,
    model_to_post,
    model_to_qa_review,
    packet_to_model,
    post_to_model,
    qa_review_to_model,
)
from app.db.models import (
    ClusterDocumentLink,
    ContentJobModel,
    DraftPackageModel,
    EventClusterModel,
    IngestionRunModel,
    JobEventModel,
    PostModel,
    QaReviewModel,
    RawDocumentModel,
    ResearchPacketModel,
)
from app.services.events.engine import EventCluster
from app.services.ingestion.rss_adapter import RawDocument
from app.services.ingestion.service import IngestionResult
from app.services.qa.service import QaReviewResult
from app.services.research.service import ResearchPacket
from app.services.writing.service import DraftPackage


def save_content_job(session: Session, job: ContentJob) -> ContentJobModel:
    model = job_to_model(job)
    session.add(model)
    session.flush()
    return model


def save_job_events(session: Session, job: ContentJob) -> None:
    for event in job.events:
        session.add(event_to_model(event, job_id=job.job_id))


def save_ingestion_result(
    session: Session,
    result: IngestionResult,
    run_id: str,
    lookback_hours: int,
) -> IngestionRunModel:
    run_model = ingestion_result_to_run_model(result, run_id, lookback_hours)
    session.add(run_model)
    for doc in result.documents:
        session.add(document_to_model(doc, ingestion_run_id=run_id))
    session.flush()
    return run_model


def save_event_clusters(
    session: Session,
    clusters: list[EventCluster],
    document_id_map: dict[str, int],
) -> list[EventClusterModel]:
    models: list[EventClusterModel] = []
    for cluster in clusters:
        cluster_model = cluster_to_model(cluster)
        session.add(cluster_model)
        session.flush()
        models.append(cluster_model)
        for doc in cluster.documents:
            raw_doc = RawDocumentModel(
                source_id=doc.source_id,
                title=doc.title,
                url=doc.url,
                summary=doc.summary,
                published_at=doc.published_at,
                authority_weight=doc.authority_weight,
            )
            session.add(raw_doc)
            session.flush()
            session.add(
                ClusterDocumentLink(
                    cluster_id_fk=cluster_model.id,
                    document_id_fk=raw_doc.id,
                )
            )
    session.flush()
    return models


def save_research_packet(session: Session, packet: ResearchPacket, job_id: str) -> ResearchPacketModel:
    model = packet_to_model(packet, job_id)
    session.add(model)
    session.flush()
    return model


def save_draft_package(session: Session, draft: DraftPackage, job_id: str) -> DraftPackageModel:
    model = draft_to_model(draft, job_id)
    session.add(model)
    session.flush()
    return model


def save_qa_review(
    session: Session,
    review: QaReviewResult,
    decision: QualityDecision,
    job_id: str,
) -> QaReviewModel:
    model = qa_review_to_model(review, job_id, decision.accepted)
    session.add(model)
    session.flush()
    return model


def get_job_by_id(session: Session, job_id: str) -> Optional[ContentJob]:
    model = session.query(ContentJobModel).filter_by(job_id=job_id).first()
    if model is None:
        return None
    return model_to_job(model)


def get_job_history(session: Session, job_id: str) -> list:
    return list(
        session.query(JobEventModel)
        .filter_by(job_id=job_id)
        .order_by(JobEventModel.created_at)
        .all()
    )


def get_research_packet(session: Session, job_id: str) -> Optional[ResearchPacket]:
    model = session.query(ResearchPacketModel).filter_by(job_id=job_id).first()
    if model is None:
        return None
    return model_to_packet(model)


def get_draft_package(session: Session, job_id: str) -> Optional[DraftPackage]:
    model = session.query(DraftPackageModel).filter_by(job_id=job_id).first()
    if model is None:
        return None
    return model_to_draft(model)


def get_qa_review(session: Session, job_id: str) -> Optional[tuple[QaReviewResult, bool]]:
    model = session.query(QaReviewModel).filter_by(job_id=job_id).first()
    if model is None:
        return None
    return model_to_qa_review(model)


def list_jobs(
    session: Session,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ContentJob]:
    query = session.query(ContentJobModel).order_by(ContentJobModel.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    models = query.offset(offset).limit(limit).all()
    return [model_to_job(m) for m in models]


def get_ingestion_run(session: Session, run_id: str) -> Optional[IngestionRunModel]:
    return session.query(IngestionRunModel).filter_by(run_id=run_id).first()


def list_ingestion_runs(session: Session, limit: int = 50) -> list[IngestionRunModel]:
    return list(
        session.query(IngestionRunModel)
        .order_by(IngestionRunModel.started_at.desc())
        .limit(limit)
        .all()
    )


def save_posts(session: Session, posts: list[Post], job_id: str) -> list[PostModel]:
    models: list[PostModel] = []
    for post in posts:
        model = post_to_model(post, job_id)
        session.add(model)
        models.append(model)
    session.flush()
    return models


def get_posts_by_job_id(session: Session, job_id: str) -> list[Post]:
    models = (
        session.query(PostModel)
        .filter_by(job_id=job_id)
        .order_by(PostModel.created_at)
        .all()
    )
    return [model_to_post(m) for m in models]


def get_post_by_id(session: Session, post_id: str) -> Optional[Post]:
    model = session.query(PostModel).filter_by(post_id=post_id).first()
    if model is None:
        return None
    return model_to_post(model)


def complete_ingestion_run(session: Session, run_id: str) -> None:
    model = session.query(IngestionRunModel).filter_by(run_id=run_id).first()
    if model:
        model.completed_at = datetime.now(timezone.utc)
