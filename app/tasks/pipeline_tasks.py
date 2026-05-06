from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.settings import AppSettings
from app.db.engine import create_db_engine, create_session_factory
from app.db.repository import save_event_clusters, save_ingestion_result
from app.services.events.engine import EventEngine
from app.services.factory import build_content_services
from app.services.ingestion.service import IngestionService
from app.tasks.celery_app import celery_app
from app.workflows.persistent_workflow import PersistentWorkflowRunner


def _build_session() -> Session:
    settings = AppSettings.from_env()
    engine = create_db_engine(settings.database_url)
    return create_session_factory(engine)()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def ingest_sources_task(self, lookback_hours: int = 24) -> dict:
    settings = AppSettings.from_env()
    now = datetime.now(timezone.utc)
    service = IngestionService(settings=settings)
    result = service.ingest_recent_documents_with_errors(now=now, lookback_hours=lookback_hours)

    db = _build_session()
    try:
        run_id = str(uuid4())
        save_ingestion_result(db, result, run_id, lookback_hours)
        db.commit()
        return {
            "run_id": run_id,
            "document_count": len(result.documents),
            "error_count": len(result.source_errors),
        }
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
def run_pipeline_for_cluster_task(self, cluster_data: dict) -> dict:
    from app.services.events.engine import EventCluster
    from app.db.repository import model_to_cluster

    settings = AppSettings.from_env()
    content_services = build_content_services(settings=settings)

    db = _build_session()
    try:
        cluster = EventCluster.from_dict(cluster_data)
        runner = PersistentWorkflowRunner(session=db, content_services=content_services)
        result = runner.run_for_cluster(cluster, topic=cluster.headline)
        return {
            "job_id": result.job.job_id,
            "status": result.job.status,
            "accepted": result.decision.accepted,
        }
    finally:
        db.close()


@celery_app.task
def run_full_pipeline_task(lookback_hours: int = 24, limit: int = 3) -> dict:
    settings = AppSettings.from_env()
    now = datetime.now(timezone.utc)
    ingestion_service = IngestionService(settings=settings)
    ingest_result = ingestion_service.ingest_recent_documents_with_errors(
        now=now, lookback_hours=lookback_hours
    )

    db = _build_session()
    try:
        ingest_run_id = str(uuid4())
        save_ingestion_result(db, ingest_result, ingest_run_id, lookback_hours)
        db.flush()

        clusters = EventEngine().select_top_clusters(
            documents=ingest_result.documents, now=now, limit=limit
        )
        save_event_clusters(db, clusters, {})
        db.flush()

        content_services = build_content_services(settings=settings)
        runner = PersistentWorkflowRunner(session=db, content_services=content_services)
        job_ids = []
        for cluster in clusters:
            result = runner.run_for_cluster(cluster, topic=cluster.headline)
            job_ids.append(result.job.job_id)

        db.commit()
        return {
            "ingest_run_id": ingest_run_id,
            "job_ids": job_ids,
            "document_count": len(ingest_result.documents),
        }
    finally:
        db.close()
