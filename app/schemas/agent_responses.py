from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchAgentOutput(BaseModel):
    event_summary: str
    primary_source_summary: str
    keywords: list[str] = Field(min_length=1, max_length=10)
    open_questions: list[str]


class WritingAgentOutput(BaseModel):
    long_title: str = Field(min_length=1)
    long_body: str = Field(min_length=1)
    short_title: str = Field(min_length=1)
    short_body: str = Field(min_length=1)


class QaReviewAgentOutput(BaseModel):
    total_score: int = Field(ge=0, le=100)
    factual_accuracy_score: int = Field(ge=0, le=100)
    viewpoint_clarity_score: int = Field(ge=0, le=100)
    sources_verified: bool
    within_time_window: bool
    claims_supported: bool
    long_short_consistent: bool
    failed_checks: list[str]
