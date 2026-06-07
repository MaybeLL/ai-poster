from __future__ import annotations

import json
import logging
from uuid import uuid4

from app.agents.provider import AgentProvider, AgentRequest
from app.posting.models import Post
from app.services.research.service import ResearchPacket

logger = logging.getLogger(__name__)

MAX_TAGS = 4

WECHAT_TEMPLATE = """{headline}

## 事件概述
{event_summary}

## 核心分析
{primary_source_summary}

## 关键要点
{keywords_section}

## 值得关注的问题
{questions_section}"""


class WeChatPostPipeline:
    """Platform pipeline for WeChat official account — long-form, structured, article-style."""

    def __init__(self, provider: AgentProvider | None = None) -> None:
        self.provider = provider

    @property
    def platform(self) -> str:
        return "wechat"

    def build_post(self, packet: ResearchPacket, job_id: str) -> Post:
        if self.provider is not None:
            return self._build_agent_post(packet, job_id)
        return self._build_rule_post(packet, job_id)

    def _build_agent_post(self, packet: ResearchPacket, job_id: str) -> Post:
        request = AgentRequest(
            task_name="post-wechat",
            prompt=self._build_prompt(packet),
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
                title=payload["title"],
                body=payload["body"],
                tags=payload.get("tags", []),
                status="draft",
            )
        except Exception:
            logger.warning("WeChat agent post failed, falling back to rule-based", exc_info=True)
            return self._build_rule_post(packet, job_id)

    def _build_rule_post(self, packet: ResearchPacket, job_id: str) -> Post:
        keywords_str = "、".join(packet.keywords[:MAX_TAGS]) if packet.keywords else "暂无"
        questions_str = "\n".join(
            f"- {q}" for q in packet.open_questions
        ) if packet.open_questions else "暂无未解决问题"

        body = WECHAT_TEMPLATE.format(
            headline=packet.headline,
            event_summary=packet.event_summary,
            primary_source_summary=packet.primary_source_summary,
            keywords_section=keywords_str,
            questions_section=questions_str,
        )
        title = f"{packet.headline}：深度解读"

        return Post(
            post_id=str(uuid4()),
            job_id=job_id,
            platform="wechat",
            title=title,
            body=body.strip(),
            tags=packet.keywords[:MAX_TAGS],
            status="draft",
        )

    @staticmethod
    def _build_prompt(packet: ResearchPacket) -> str:
        return json.dumps(
            {
                "instructions": (
                    "You are a tech analyst writing for a WeChat official account. "
                    "Given the research data below, produce a long-form article.\n\n"
                    "Title (15-25 Chinese characters):\n"
                    "- Start with a concrete angle, not the generic headline.\n"
                    '- Bad: "GPT-5发布深度解读"\n'
                    '- Good: "GPT-5推理能力质的飞跃，OpenAI的底牌是什么"\n\n'
                    "Body (1500-2500 characters, Chinese):\n"
                    "Structure with ## Markdown headers. Follow this sequence:\n"
                    "1. ## 事件概述 — One paragraph hook: what happened and why it matters now.\n"
                    '2. ## 核心看点 — 2-3 concrete angles: what is new, what changed, why different from before.\n'
                    "3. ## 为什么重要 — Broader implications: who is affected, what shifts.\n"
                    "4. ## 值得关注的问题 — Open questions from the research, no filler.\n\n"
                    "Writing rules:\n"
                    "- Professional, analytical voice. No emoji, no exclamation marks.\n"
                    '- Avoid: "值得注意的是", "我们不难发现", "毋庸置疑", empty phrases.\n'
                    "- Every paragraph must carry a specific claim, not a generality.\n"
                    "- End with a sharp closing sentence, not a summary.\n\n"
                    "Tags: 2-4 Chinese topic tags, no # symbol.\n"
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
