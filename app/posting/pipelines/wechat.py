from __future__ import annotations

import json
import logging
from uuid import uuid4

from app.agents.provider import AgentProvider, AgentRequest
from app.posting.models import Post
from app.services.research.service import ResearchPacket
from app.services.writing.service import DraftPackage

logger = logging.getLogger(__name__)

MAX_TAGS = 4


class WeChatPostPipeline:
    """Platform pipeline for WeChat official account — uses writing draft as base, agent polishes."""

    def __init__(self, provider: AgentProvider | None = None) -> None:
        self.provider = provider

    @property
    def platform(self) -> str:
        return "wechat"

    def build_post(self, packet: ResearchPacket, draft: DraftPackage, job_id: str) -> Post:
        if self.provider is not None:
            return self._build_agent_post(packet, draft, job_id)
        return self._build_rule_post(packet, draft, job_id)

    def _build_agent_post(self, packet: ResearchPacket, draft: DraftPackage, job_id: str) -> Post:
        prompt = json.dumps(
            {
                "instructions": (
                    "You are an editor polishing a WeChat official account article about AI industry news. "
                    "The article below is already well-written. Your job:\n\n"
                    "1. Polish the title (15-25 Chinese characters): make it sharper, more concrete, "
                    "with a specific angle. Keep the original meaning.\n\n"
                    "2. Polish the body: improve transitions, sharpen the opening hook and closing line. "
                    "Keep all factual claims intact. Maintain the original structure and sections.\n"
                    "Add markdown headers (##) if missing. The body should be 800-1500 Chinese characters.\n\n"
                    "3. Tags: 2-4 Chinese topic tags, no # symbol.\n\n"
                    "Writing rules:\n"
                    "- Professional, analytical voice. No emoji, no exclamation marks.\n"
                    '- Avoid: "值得注意的是", "我们不难发现", "毋庸置疑" — empty phrases.\n'
                    "- Every paragraph must carry a specific claim.\n"
                    "- End with a sharp closing sentence, not a summary.\n\n"
                    "Output valid JSON matching the response schema."
                ),
                "draft_title": draft.long_article.title,
                "draft_body": draft.long_article.body,
            },
            ensure_ascii=False,
        )
        request = AgentRequest(
            task_name="post-wechat",
            prompt=prompt,
            metadata={"cluster_id": packet.cluster_id, "platform": "wechat"},
            response_schema=self._response_schema(),
        )
        try:
            response = self.provider.generate(request)
            payload = json.loads(response.output_text)
            return Post(
                post_id=str(uuid4()),
                job_id=job_id,
                platform="wechat",
                title=payload.get("title", draft.long_article.title),
                body=payload.get("body", draft.long_article.body),
                tags=payload.get("tags", packet.keywords[:MAX_TAGS]),
                status="draft",
            )
        except Exception:
            logger.warning("WeChat agent post failed, falling back to draft reuse", exc_info=True)
            return self._build_rule_post(packet, draft, job_id)

    def _build_rule_post(self, packet: ResearchPacket, draft: DraftPackage, job_id: str) -> Post:
        return Post(
            post_id=str(uuid4()),
            job_id=job_id,
            platform="wechat",
            title=draft.long_article.title,
            body=draft.long_article.body.strip(),
            tags=packet.keywords[:MAX_TAGS],
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
