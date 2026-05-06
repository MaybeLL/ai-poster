from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


PIPELINE_STATUSES = (
    "created",
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
    "accepted",
    "rejected",
    "exported",
)

TERMINAL_STATUSES = {"accepted", "rejected", "exported"}


class InvalidTransitionError(ValueError):
    """Raised when a content job attempts an invalid state transition."""


@dataclass(frozen=True)
class JobEvent:
    from_status: str
    to_status: str
    reason: str
    created_at: datetime
    rewind: bool = False

    def to_dict(self) -> dict:
        return {
            "from_status": self.from_status,
            "to_status": self.to_status,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "rewind": self.rewind,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobEvent":
        return cls(
            from_status=data["from_status"],
            to_status=data["to_status"],
            reason=data["reason"],
            created_at=datetime.fromisoformat(data["created_at"]),
            rewind=data.get("rewind", False),
        )


@dataclass
class ContentJob:
    job_id: str
    topic: str
    status: str = "created"
    events: List[JobEvent] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "topic": self.topic,
            "status": self.status,
            "events": [e.to_dict() for e in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContentJob":
        job = cls(job_id=data["job_id"], topic=data["topic"])
        job.status = data.get("status", "created")
        job.events = [JobEvent.from_dict(e) for e in data.get("events", [])]
        return job

    def transition_to(self, next_status: str, reason: str) -> JobEvent:
        self._assert_known_status(next_status)
        self._assert_forward_transition(next_status)
        event = self._record_event(next_status=next_status, reason=reason, rewind=False)
        self.status = next_status
        return event

    def rewind_to(self, target_status: str, reason: str) -> JobEvent:
        self._assert_known_status(target_status)
        current_index = PIPELINE_STATUSES.index(self.status)
        target_index = PIPELINE_STATUSES.index(target_status)

        if target_index >= current_index:
            raise InvalidTransitionError(
                "rewind target must be an earlier stage in the pipeline"
            )
        if target_status in TERMINAL_STATUSES or target_status == "created":
            raise InvalidTransitionError("rewind target must be a safe non-terminal stage")

        event = self._record_event(next_status=target_status, reason=reason, rewind=True)
        self.status = target_status
        return event

    def _assert_known_status(self, status: str) -> None:
        if status not in PIPELINE_STATUSES:
            raise InvalidTransitionError(f"unknown status: {status}")

    def _assert_forward_transition(self, next_status: str) -> None:
        if self.status in TERMINAL_STATUSES:
            raise InvalidTransitionError("cannot transition from a terminal status")

        current_index = PIPELINE_STATUSES.index(self.status)
        next_index = PIPELINE_STATUSES.index(next_status)

        is_next_sequential_stage = next_index == current_index + 1
        accepts_review = self.status == "reviewed" and next_status in {"accepted", "rejected"}
        exports_after_accept = self.status == "accepted" and next_status == "exported"

        if not (is_next_sequential_stage or accepts_review or exports_after_accept):
            raise InvalidTransitionError(
                f"invalid transition from {self.status} to {next_status}"
            )

    def _record_event(self, next_status: str, reason: str, rewind: bool) -> JobEvent:
        event = JobEvent(
            from_status=self.status,
            to_status=next_status,
            reason=reason,
            created_at=datetime.now(timezone.utc),
            rewind=rewind,
        )
        self.events.append(event)
        return event
