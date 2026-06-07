from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.settings import AppSettings
from app.db.repository import (
    list_ingestion_runs,
    save_event_clusters,
    save_ingestion_result,
)
from app.posting.publishers import TelegramPublisher
from app.services.events.engine import EventEngine
from app.services.factory import build_content_services
from app.services.ingestion.service import IngestionService
from app.web.deps import get_db, get_settings
from app.web.schemas import IngestTriggerResponse, PipelineTriggerResponse, RunResponse
from app.workflows.persistent_workflow import PersistentWorkflowRunner

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


@router.post("/ingest", response_model=IngestTriggerResponse)
def trigger_ingest(
    lookback_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
    settings: AppSettings = Depends(get_settings),
):
    run_id = str(uuid4())
    now = datetime.now(timezone.utc)
    service = IngestionService(settings=settings)
    result = service.ingest_recent_documents_with_errors(now=now, lookback_hours=lookback_hours)
    save_ingestion_result(db, result, run_id, lookback_hours)
    db.commit()
    return IngestTriggerResponse(
        message=f"Ingested {len(result.documents)} documents from {lookback_hours}h window",
        run_id=run_id,
    )


@router.post("/pipeline", response_model=PipelineTriggerResponse)
def trigger_pipeline(
    lookback_hours: int = Query(24, ge=1, le=168),
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    settings: AppSettings = Depends(get_settings),
):
    now = datetime.now(timezone.utc)
    ingestion_service = IngestionService(settings=settings)
    ingest_result = ingestion_service.ingest_recent_documents_with_errors(
        now=now, lookback_hours=lookback_hours
    )

    ingest_run_id = str(uuid4())
    save_ingestion_result(db, ingest_result, ingest_run_id, lookback_hours)
    db.flush()

    clusters = EventEngine().select_top_clusters(
        documents=ingest_result.documents, now=now, limit=limit
    )
    save_event_clusters(db, clusters, {})
    db.flush()

    content_services = build_content_services(settings=settings)
    tg = (
        TelegramPublisher(bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id)
        if settings.telegram_bot_token and settings.telegram_chat_id
        else None
    )
    runner = PersistentWorkflowRunner(
        session=db,
        content_services=content_services,
        output_dir=settings.data_dir,
        publishers=[tg] if tg else [],
    )

    job_ids: list[str] = []
    for cluster in clusters:
        result = runner.run_for_cluster(cluster, topic=cluster.headline)
        job_ids.append(result.job.job_id)

    db.commit()
    return PipelineTriggerResponse(
        message=f"Pipeline completed: {len(job_ids)} job(s) created",
        job_ids=job_ids,
    )


@router.get("", response_model=list[RunResponse])
def list_runs_route(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    runs = list_ingestion_runs(db, limit=limit)
    return [
        RunResponse(
            run_id=r.run_id,
            status="completed" if r.completed_at else "running",
            lookback_hours=r.lookback_hours,
            document_count=r.document_count,
            error_count=r.error_count,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=RunResponse)
def get_run_route(run_id: str, db: Session = Depends(get_db)):
    from app.db.repository import get_ingestion_run

    run = get_ingestion_run(db, run_id=run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(
        run_id=run.run_id,
        status="completed" if run.completed_at else "running",
        lookback_hours=run.lookback_hours,
        document_count=run.document_count,
        error_count=run.error_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )
