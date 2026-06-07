from __future__ import annotations

import json
import logging
from uuid import uuid4

from app.agents.provider import AgentProvider, AgentRequest
from app.posting.models import Post
from app.services.research.service import ResearchPacket

logger = logging.getLogger(__name__)


class XiaohongshuPostPipeline:
    """Platform pipeline for Xiaohongshu (RED) — short-form, casual, emoji-friendly."""

    def __init__(self, provider: AgentProvider | None = None) -> None:
        self.provider = provider

    @property
    def platform(self) -> str:
        return "xiaohongshu"

    def build_post(self, packet: ResearchPacket, job_id: str) -> Post:
        if self.provider is not None:
            return self._build_agent_post(packet, job_id)
        return self._build_rule_post(packet, job_id)

    def _build_agent_post(self, packet: ResearchPacket, job_id: str) -> Post:
        request = AgentRequest(
            task_name="post-xiaohongshu",
            prompt=self._build_prompt(packet),
            metadata={"cluster_id": packet.cluster_id, "platform": "xiaohongshu"},
            response_schema=self._response_schema(),
        )
        try:
            response = self.provider.generate(request)
            payload = json.loads(response.output_text)
            return Post(
                post_id=str(uuid4()),
                job_id=job_id,
                platform="xiaohongshu",
                title=payload["title"],
                body=payload["body"],
                tags=payload.get("tags", []),
                status="draft",
            )
        except Exception:
            logger.warning(
                "Xiaohongshu agent post failed, falling back to rule-based", exc_info=True
            )
            return self._build_rule_post(packet, job_id)

    def _build_rule_post(self, packet: ResearchPacket, job_id: str) -> Post:
        body_lines = [
            f"📌 {packet.headline}",
            "",
            packet.event_summary,
            "",
            f"💡 {packet.primary_source_summary}",
        ]
        if packet.keywords:
            tags_str = " ".join(f"#{k}" for k in packet.keywords[:4])
            body_lines.extend(["", tags_str])

        return Post(
            post_id=str(uuid4()),
            job_id=job_id,
            platform="xiaohongshu",
            title=packet.headline,
            body="\n".join(body_lines),
            tags=packet.keywords[:4],
            status="draft",
        )

    @staticmethod
    def _build_prompt(packet: ResearchPacket) -> str:
        return json.dumps(
            {
                "instructions": (
                    "You are a tech-savvy friend sharing AI news on Xiaohongshu (RED). "
                    "Given the research data below, write a short post.\n\n"
                    "Title (10-20 Chinese characters):\n"
                    "- Conversational, like saying something interesting to a friend.\n"
                    '- Bad: "GPT-5发布信息汇总"\n'
                    '- Good: "GPT-5悄悄上线，我发现了这些细节"\n\n'
                    "Body (300-800 characters, Chinese):\n"
                    "Structure with line breaks (no markdown headers):\n"
                    "1. Hook (1-2 lines) — Get attention fast. A surprising angle or concrete observation.\n"
                    "2. What happened (3-5 lines) — Key facts, specific numbers or claims.\n"
                    "3. Why care (2-3 lines) — Personal take, what this means for the reader.\n"
                    "4. Bottom line (1-2 lines) — Sharp closing opinion.\n\n"
                    "Writing rules:\n"
                    "- Casual, curious, slightly excited tone. Not corporate, not overly promotional.\n"
                    "- Use 1-2 emoji max, placed where they amplify the tone (📌💡), not decoration.\n"
                    '- Avoid: "家人们", "谁懂啊", "绝了", clickbait phrases.\n'
                    "- Short paragraphs (1-3 lines each), blank line between them.\n"
                    "- Readable on mobile: no markdown, no tables, pure plain text with line breaks.\n\n"
                    "Tags: 2-4 Chinese hashtags with # prefix (e.g. ['#AI', '#GPT5', '#科技资讯']).\n"
                    "Output valid JSON matching the response schema."
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
                "title": {"type": "string"},
                "body": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "body"],
        }
