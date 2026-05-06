from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.repository import (
    get_job_by_id,
    get_job_history,
    get_research_packet,
    get_draft_package,
    get_qa_review,
    list_jobs,
)
from app.web.deps import get_db
from app.web.schemas import (
    JobDetailResponse,
    JobEventResponse,
    JobResponse,
)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("", response_model=list[JobResponse])
def list_jobs_route(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    jobs = list_jobs(db, status=status, limit=limit, offset=offset)
    return [
        JobResponse(job_id=job.job_id, topic=job.topic, status=job.status)
        for job in jobs
    ]


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job_route(job_id: str, db: Session = Depends(get_db)):
    job = get_job_by_id(db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetailResponse(
        job_id=job.job_id,
        topic=job.topic,
        status=job.status,
        event_count=len(job.events),
    )


@router.get("/{job_id}/events", response_model=list[JobEventResponse])
def get_job_events_route(job_id: str, db: Session = Depends(get_db)):
    job = get_job_by_id(db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    events = get_job_history(db, job_id=job_id)
    return [
        JobEventResponse(
            id=e.id,
            from_status=e.from_status,
            to_status=e.to_status,
            reason=e.reason,
            rewind=e.rewind,
            created_at=e.created_at,
        )
        for e in events
    ]


@router.get("/{job_id}/research")
def get_job_research_route(job_id: str, db: Session = Depends(get_db)):
    job = get_job_by_id(db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    packet = get_research_packet(db, job_id=job_id)
    if packet is None:
        raise HTTPException(status_code=404, detail="Research packet not found")
    return packet.to_dict()


@router.get("/{job_id}/draft")
def get_job_draft_route(job_id: str, db: Session = Depends(get_db)):
    job = get_job_by_id(db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    draft = get_draft_package(db, job_id=job_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft.to_dict()


@router.get("/{job_id}/qa")
def get_job_qa_route(job_id: str, db: Session = Depends(get_db)):
    job = get_job_by_id(db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    result = get_qa_review(db, job_id=job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="QA review not found")
    review, accepted = result
    return {**review.to_dict(), "accepted": accepted}
