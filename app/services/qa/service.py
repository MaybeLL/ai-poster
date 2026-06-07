from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from app.agents.provider import AgentProvider, AgentRequest
from app.core.quality_gate import QualityGateInput
from app.schemas.agent_responses import QaReviewAgentOutput
from app.services.research.service import ResearchPacket
from app.services.writing.service import DraftPackage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QaReviewResult:
    total_score: int
    factual_accuracy_score: int
    viewpoint_clarity_score: int
    sources_verified: bool
    within_time_window: bool
    claims_supported: bool
    long_short_consistent: bool
    failed_checks: list[str] = field(default_factory=list)

    def to_quality_gate_input(self) -> QualityGateInput:
        return QualityGateInput(
            total_score=self.total_score,
            factual_accuracy_score=self.factual_accuracy_score,
            viewpoint_clarity_score=self.viewpoint_clarity_score,
            sources_verified=self.sources_verified,
            within_time_window=self.within_time_window,
            claims_supported=self.claims_supported,
            long_short_consistent=self.long_short_consistent,
        )

    def to_dict(self) -> dict:
        return {
            "total_score": self.total_score,
            "factual_accuracy_score": self.factual_accuracy_score,
            "viewpoint_clarity_score": self.viewpoint_clarity_score,
            "sources_verified": self.sources_verified,
            "within_time_window": self.within_time_window,
            "claims_supported": self.claims_supported,
            "long_short_consistent": self.long_short_consistent,
            "failed_checks": list(self.failed_checks),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QaReviewResult":
        return cls(
            total_score=data["total_score"],
            factual_accuracy_score=data["factual_accuracy_score"],
            viewpoint_clarity_score=data["viewpoint_clarity_score"],
            sources_verified=data["sources_verified"],
            within_time_window=data["within_time_window"],
            claims_supported=data["claims_supported"],
            long_short_consistent=data["long_short_consistent"],
            failed_checks=data.get("failed_checks", []),
        )


class QaService:
    def review_package(self, packet: ResearchPacket, draft_package: DraftPackage) -> QaReviewResult:
        headline = packet.headline
        long_text = f"{draft_package.long_article.title}\n{draft_package.long_article.body}"
        short_text = f"{draft_package.short_post.title}\n{draft_package.short_post.body}"

        claims_supported = headline in long_text and packet.primary_source_summary in long_text
        long_short_consistent = headline in short_text
        sources_verified = len(packet.source_briefs) >= 1
        within_time_window = "missing_publication_time" not in packet.open_questions
        factual_accuracy_score = 95 if claims_supported else 70
        viewpoint_clarity_score = 82 if "一句话判断" in draft_package.short_post.body else 68
        total_score = 60
        if claims_supported:
            total_score += 15
        if long_short_consistent:
            total_score += 10
        if sources_verified:
            total_score += 8
        if within_time_window:
            total_score += 4
        if viewpoint_clarity_score >= 75:
            total_score += 5

        failed_checks: list[str] = []
        if not claims_supported:
            failed_checks.append("claims_supported")
        if not long_short_consistent:
            failed_checks.append("long_short_consistent")
        if not sources_verified:
            failed_checks.append("sources_verified")
        if not within_time_window:
            failed_checks.append("within_time_window")

        return QaReviewResult(
            total_score=total_score,
            factual_accuracy_score=factual_accuracy_score,
            viewpoint_clarity_score=viewpoint_clarity_score,
            sources_verified=sources_verified,
            within_time_window=within_time_window,
            claims_supported=claims_supported,
            long_short_consistent=long_short_consistent,
            failed_checks=failed_checks,
        )


class AgentQaService:
    def __init__(
        self,
        provider: AgentProvider,
        fallback: QaService | None = None,
    ) -> None:
        self.provider = provider
        self.fallback = fallback or QaService()

    def review_package(self, packet: ResearchPacket, draft_package: DraftPackage) -> QaReviewResult:
        request = AgentRequest(
            task_name="review",
            prompt=self._build_prompt(packet, draft_package),
            metadata={"cluster_id": packet.cluster_id},
            response_schema=self._response_schema(),
        )
        try:
            response = self.provider.generate(request)
            raw = json.loads(response.output_text)
            if isinstance(raw, dict) and "structured_output" in raw:
                raw = raw["structured_output"]
            payload = QaReviewAgentOutput.model_validate(raw)
            return QaReviewResult(
                total_score=payload.total_score,
                factual_accuracy_score=payload.factual_accuracy_score,
                viewpoint_clarity_score=payload.viewpoint_clarity_score,
                sources_verified=payload.sources_verified,
                within_time_window=payload.within_time_window,
                claims_supported=payload.claims_supported,
                long_short_consistent=payload.long_short_consistent,
                failed_checks=payload.failed_checks,
            )
        except Exception:
            logger.warning("Agent QA review failed, falling back to rule-based", exc_info=True)
            return self.fallback.review_package(packet=packet, draft_package=draft_package)

    @staticmethod
    def _build_prompt(packet: ResearchPacket, draft_package: DraftPackage) -> str:
        return json.dumps(
            {
                "instructions": (
                    "You are an editorial QA reviewer for AI industry content. "
                    "Review the long-form article and short post against the research packet.\n"
                    "Score each dimension:\n"
                    "- total_score (0-100): Overall quality.\n"
                    "- factual_accuracy_score (0-100): How well claims match the source briefs.\n"
                    "- viewpoint_clarity_score (0-100): Is the core judgment clear and well-articulated?\n"
                    "- sources_verified (bool): Are claims traceable to sources?\n"
                    "- within_time_window (bool): Is the content timely?\n"
                    "- claims_supported (bool): Are major claims backed by evidence?\n"
                    "- long_short_consistent (bool): Do both versions share the same fact base?\n"
                    "- failed_checks (list[str]): Names of any failed checks.\n"
                    "Output valid JSON matching the response schema."
                ),
                "data": {
                    "headline": packet.headline,
                    "primary_source_summary": packet.primary_source_summary,
                    "open_questions": packet.open_questions,
                    "long_article": {
                        "title": draft_package.long_article.title,
                        "body": draft_package.long_article.body,
                    },
                    "short_post": {
                        "title": draft_package.short_post.title,
                        "body": draft_package.short_post.body,
                    },
                },
            },
            ensure_ascii=True,
        )

    @staticmethod
    def _response_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "total_score": {"type": "integer"},
                "factual_accuracy_score": {"type": "integer"},
                "viewpoint_clarity_score": {"type": "integer"},
                "sources_verified": {"type": "boolean"},
                "within_time_window": {"type": "boolean"},
                "claims_supported": {"type": "boolean"},
                "long_short_consistent": {"type": "boolean"},
                "failed_checks": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "total_score",
                "factual_accuracy_score",
                "viewpoint_clarity_score",
                "sources_verified",
                "within_time_window",
                "claims_supported",
                "long_short_consistent",
                "failed_checks",
            ],
        }
