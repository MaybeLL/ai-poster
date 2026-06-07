from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class QualityGateInput:
    total_score: int
    factual_accuracy_score: int
    viewpoint_clarity_score: int
    sources_verified: bool
    within_time_window: bool
    claims_supported: bool
    long_short_consistent: bool


@dataclass(frozen=True)
class QualityDecision:
    accepted: bool
    failed_checks: List[str] = field(default_factory=list)


class QualityGate:
    """Applies hard guards before allowing a content package to pass."""

    min_total_score = 60
    min_factual_accuracy_score = 65
    min_viewpoint_clarity_score = 65

    def evaluate(self, payload: QualityGateInput) -> QualityDecision:
        failed_checks: List[str] = []

        if not payload.sources_verified:
            failed_checks.append("sources_verified")
        if not payload.within_time_window:
            failed_checks.append("within_time_window")
        if not payload.claims_supported:
            failed_checks.append("claims_supported")
        if not payload.long_short_consistent:
            failed_checks.append("long_short_consistent")
        if payload.total_score < self.min_total_score:
            failed_checks.append("total_score")
        if payload.factual_accuracy_score < self.min_factual_accuracy_score:
            failed_checks.append("factual_accuracy_score")
        if payload.viewpoint_clarity_score < self.min_viewpoint_clarity_score:
            failed_checks.append("viewpoint_clarity_score")

        return QualityDecision(
            accepted=not failed_checks,
            failed_checks=failed_checks,
        )
