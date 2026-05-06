from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: str
    topic: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobDetailResponse(JobResponse):
    event_count: int = 0


class JobEventResponse(BaseModel):
    id: int
    from_status: str
    to_status: str
    reason: str
    rewind: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RunResponse(BaseModel):
    run_id: str
    status: str
    lookback_hours: int
    document_count: int
    error_count: int
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PipelineTriggerResponse(BaseModel):
    message: str
    job_ids: list[str] = []


class IngestTriggerResponse(BaseModel):
    message: str
    run_id: str
