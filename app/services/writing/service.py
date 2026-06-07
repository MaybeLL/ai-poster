from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.agents.provider import AgentProvider, AgentRequest
from app.schemas.agent_responses import WritingAgentOutput
from app.services.research.service import ResearchPacket

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DraftArticle:
    cluster_id: str
    title: str
    body: str

    def to_dict(self) -> dict:
        return {"cluster_id": self.cluster_id, "title": self.title, "body": self.body}

    @classmethod
    def from_dict(cls, data: dict) -> "DraftArticle":
        return cls(cluster_id=data["cluster_id"], title=data["title"], body=data["body"])


@dataclass(frozen=True)
class DraftPackage:
    long_article: DraftArticle
    short_post: DraftArticle

    def to_dict(self) -> dict:
        return {
            "long_article": self.long_article.to_dict(),
            "short_post": self.short_post.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DraftPackage":
        return cls(
            long_article=DraftArticle.from_dict(data["long_article"]),
            short_post=DraftArticle.from_dict(data["short_post"]),
        )


class WritingService:
    def build_draft_package(self, packet: ResearchPacket) -> DraftPackage:
        long_title = f"{packet.headline}：这件事为什么值得关注"
        long_body = "\n".join(
            (
                packet.headline,
                "",
                "事件概述",
                packet.event_summary,
                "",
                "为什么值得关注",
                packet.primary_source_summary,
                "",
                "值得继续跟踪的点",
                "、".join(packet.keywords) if packet.keywords else "暂无关键词",
            )
        )
        short_title = packet.headline
        short_body = "\n".join(
            (
                f"一句话判断：{packet.headline} 值得继续跟踪。",
                f"核心信息：{packet.primary_source_summary}",
            )
        )
        return DraftPackage(
            long_article=DraftArticle(
                cluster_id=packet.cluster_id,
                title=long_title,
                body=long_body,
            ),
            short_post=DraftArticle(
                cluster_id=packet.cluster_id,
                title=short_title,
                body=short_body,
            ),
        )


class AgentWritingService:
    def __init__(
        self,
        provider: AgentProvider,
        fallback: WritingService | None = None,
    ) -> None:
        self.provider = provider
        self.fallback = fallback or WritingService()

    def build_draft_package(self, packet: ResearchPacket) -> DraftPackage:
        request = AgentRequest(
            task_name="writing",
            prompt=self._build_prompt(packet),
            metadata={"cluster_id": packet.cluster_id},
            response_schema=self._response_schema(),
        )
        try:
            response = self.provider.generate(request)
            raw = json.loads(response.output_text)
            if isinstance(raw, dict) and "structured_output" in raw:
                raw = raw["structured_output"]
            payload = WritingAgentOutput.model_validate(raw)
            return DraftPackage(
                long_article=DraftArticle(
                    cluster_id=packet.cluster_id,
                    title=payload.long_title,
                    body=payload.long_body,
                ),
                short_post=DraftArticle(
                    cluster_id=packet.cluster_id,
                    title=payload.short_title,
                    body=payload.short_body,
                ),
            )
        except Exception:
            logger.warning("Agent writing failed, falling back to rule-based", exc_info=True)
            return self.fallback.build_draft_package(packet)

    @staticmethod
    def _build_prompt(packet: ResearchPacket) -> str:
        return json.dumps(
            {
                "instructions": (
                    "You are a tech content writer specializing in AI industry news. "
                    "Given the research packet below, produce two versions of the story:\n"
                    "- long_title: A compelling title for a WeChat public account long-form article.\n"
                    "- long_body: Full article body (~800-1500 words) with sections: what happened, "
                    "why it matters, industry implications, and key takeaways.\n"
                    "- short_title: A punchy title for a Xiaohongshu (RED) short post.\n"
                    "- short_body: Concise post (~100-200 words) with the core judgment and 2-4 key points.\n"
                    "Both versions must share the same fact base. Output valid JSON matching the response schema."
                ),
                "data": {
                    "headline": packet.headline,
                    "event_summary": packet.event_summary,
                    "primary_source_summary": packet.primary_source_summary,
                    "keywords": packet.keywords,
                    "open_questions": packet.open_questions,
                },
            },
            ensure_ascii=True,
        )

    @staticmethod
    def _response_schema() -> dict:
        return {
            "type": "object",
            "properties": {
                "long_title": {"type": "string"},
                "long_body": {"type": "string"},
                "short_title": {"type": "string"},
                "short_body": {"type": "string"},
            },
            "required": [
                "long_title",
                "long_body",
                "short_title",
                "short_body",
            ],
        }
