from __future__ import annotations

import json
import logging
from uuid import uuid4

from app.agents.provider import AgentProvider, AgentRequest
from app.posting.models import Post
from app.services.research.service import ResearchPacket
from app.services.writing.service import DraftPackage

logger = logging.getLogger(__name__)


class XiaohongshuPostPipeline:
    """Platform pipeline for Xiaohongshu (RED) — uses writing draft as base, agent polishes."""

    def __init__(self, provider: AgentProvider | None = None) -> None:
        self.provider = provider

    @property
    def platform(self) -> str:
        return "xiaohongshu"

    def build_post(self, packet: ResearchPacket, draft: DraftPackage, job_id: str) -> Post:
        if self.provider is not None:
            return self._build_agent_post(packet, draft, job_id)
        return self._build_rule_post(packet, draft, job_id)

    def _build_agent_post(self, packet: ResearchPacket, draft: DraftPackage, job_id: str) -> Post:
        prompt = json.dumps(
            {
                "instructions": (
                    "You are an editor polishing a Xiaohongshu (RED) short post about AI industry news. "
                    "The draft below is already well-written. Your job:\n\n"
                    "1. Polish the title (10-20 Chinese characters): conversational, intriguing, "
                    "like telling a friend something surprising. Keep the core fact.\n\n"
                    "2. Polish the body (200-500 Chinese characters): \n"
                    "   - Strong hook in the first 2 lines\n"
                    "   - Key facts in 3-5 lines\n"
                    "   - Personal take: why this matters to the reader\n"
                    "   - Sharp closing line\n\n"
                    "3. Tags: 2-4 Chinese hashtags with # prefix (e.g. ['#AI', '#科技']).\n\n"
                    "Writing rules:\n"
                    "- Casual, curious tone. Like chatting with a friend.\n"
                    "- Use 1-2 emoji max where they amplify tone.\n"
                    '- Avoid: "家人们", "谁懂啊", "绝了", clickbait phrases.\n'
                    "- Short paragraphs (1-3 lines), blank line between them.\n"
                    "- Plain text, no markdown headers.\n\n"
                    "Output valid JSON matching the response schema."
                ),
                "draft_title": draft.short_post.title,
                "draft_body": draft.short_post.body,
            },
            ensure_ascii=False,
        )
        request = AgentRequest(
            task_name="post-xiaohongshu",
            prompt=prompt,
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
                title=payload.get("title", draft.short_post.title),
                body=payload.get("body", draft.short_post.body),
                tags=payload.get("tags", []),
                status="draft",
            )
        except Exception:
            logger.warning(
                "Xiaohongshu agent post failed, falling back to draft reuse", exc_info=True
            )
            return self._build_rule_post(packet, draft, job_id)

    def _build_rule_post(self, packet: ResearchPacket, draft: DraftPackage, job_id: str) -> Post:
        tags = [f"#{k}" for k in packet.keywords[:4]] if packet.keywords else []

        return Post(
            post_id=str(uuid4()),
            job_id=job_id,
            platform="xiaohongshu",
            title=draft.short_post.title,
            body=draft.short_post.body.strip(),
            tags=tags,
            status="draft",
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
