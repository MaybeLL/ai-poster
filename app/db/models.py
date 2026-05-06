from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SourceModel(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(512))
    kind: Mapped[str] = mapped_column(String(32))
    url: Mapped[str] = mapped_column(Text)
    authority_weight: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class RawDocumentModel(Base):
    __tablename__ = "raw_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    authority_weight: Mapped[int] = mapped_column(Integer, default=1)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    ingestion_run_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    cluster_links: Mapped[list["ClusterDocumentLink"]] = relationship(back_populates="document")


class EventClusterModel(Base):
    __tablename__ = "event_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cluster_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    headline: Mapped[str] = mapped_column(Text)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    freshness_score: Mapped[float] = mapped_column(Float, default=0.0)
    authority_score: Mapped[float] = mapped_column(Float, default=0.0)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    document_links: Mapped[list["ClusterDocumentLink"]] = relationship(back_populates="cluster")


class ClusterDocumentLink(Base):
    __tablename__ = "cluster_documents"

    cluster_id_fk: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_clusters.id"), primary_key=True
    )
    document_id_fk: Mapped[int] = mapped_column(
        Integer, ForeignKey("raw_documents.id"), primary_key=True
    )

    cluster: Mapped["EventClusterModel"] = relationship(back_populates="document_links")
    document: Mapped["RawDocumentModel"] = relationship(back_populates="cluster_links")


class ContentJobModel(Base):
    __tablename__ = "content_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    topic: Mapped[str] = mapped_column(Text)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    events: Mapped[list["JobEventModel"]] = relationship(
        back_populates="job", order_by="JobEventModel.created_at"
    )


class JobEventModel(Base):
    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_jobs.job_id"), index=True)
    from_status: Mapped[str] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    rewind: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    job: Mapped["ContentJobModel"] = relationship(back_populates="events")


class ResearchPacketModel(Base):
    __tablename__ = "research_packets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_jobs.job_id"), index=True)
    cluster_id: Mapped[str] = mapped_column(String(64))
    headline: Mapped[str] = mapped_column(Text)
    event_summary: Mapped[str] = mapped_column(Text)
    primary_source_summary: Mapped[str] = mapped_column(Text)
    source_briefs_json: Mapped[str] = mapped_column(Text)
    timeline_json: Mapped[str] = mapped_column(Text)
    keywords_json: Mapped[str] = mapped_column(Text)
    open_questions_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class DraftPackageModel(Base):
    __tablename__ = "draft_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_jobs.job_id"), index=True)
    cluster_id: Mapped[str] = mapped_column(String(64))
    long_title: Mapped[str] = mapped_column(Text)
    long_body: Mapped[str] = mapped_column(Text)
    short_title: Mapped[str] = mapped_column(Text)
    short_body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class QaReviewModel(Base):
    __tablename__ = "qa_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_jobs.job_id"), unique=True, index=True)
    total_score: Mapped[int] = mapped_column(Integer)
    factual_accuracy_score: Mapped[int] = mapped_column(Integer)
    viewpoint_clarity_score: Mapped[int] = mapped_column(Integer)
    sources_verified: Mapped[bool] = mapped_column(Boolean)
    within_time_window: Mapped[bool] = mapped_column(Boolean)
    claims_supported: Mapped[bool] = mapped_column(Boolean)
    long_short_consistent: Mapped[bool] = mapped_column(Boolean)
    failed_checks_json: Mapped[str] = mapped_column(Text)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class IngestionRunModel(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    lookback_hours: Mapped[int] = mapped_column(Integer)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    source_errors_json: Mapped[str] = mapped_column(Text, default="[]")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
