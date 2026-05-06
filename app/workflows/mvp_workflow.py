from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.core.content_job import ContentJob
from app.core.quality_gate import QualityDecision, QualityGate, QualityGateInput


@dataclass(frozen=True)
class WorkflowRunResult:
    job: ContentJob
    decision: QualityDecision
    completed_stages: list[str]


class MvpWorkflowRunner:
    """Runs the smallest end-to-end workflow supported by the current codebase."""

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

    def __init__(self, quality_gate: QualityGate | None = None) -> None:
        self.quality_gate = quality_gate or QualityGate()

    def run(self, topic: str, qa_input: QualityGateInput) -> WorkflowRunResult:
        job = ContentJob(job_id=str(uuid4()), topic=topic)

        for stage in self.pipeline_stages:
            job.transition_to(stage, reason=f"Completed {stage} stage")

        decision = self.quality_gate.evaluate(qa_input)
        terminal_status = "accepted" if decision.accepted else "rejected"
        job.transition_to(terminal_status, reason="Quality gate decision recorded")

        completed_stages = [event.to_status for event in job.events]
        return WorkflowRunResult(
            job=job,
            decision=decision,
            completed_stages=completed_stages,
        )
