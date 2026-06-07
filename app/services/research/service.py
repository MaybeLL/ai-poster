from __future__ import annotations

import html
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from app.agents.provider import AgentProvider, AgentRequest
from app.schemas.agent_responses import ResearchAgentOutput
from app.services.events.engine import EventCluster

logger = logging.getLogger(__name__)


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]{4,}")
CHINESE_TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}")
STOP_WORDS = {
    "launches", "launch", "developers", "official", "cloud",
    "with", "this", "that", "from", "been", "have", "were",
    "more", "some", "into", "over", "also", "just", "what",
    "they", "will", "your", "about", "their", "which",
}
AI_DOMAIN_KEYWORDS = {
    "ai", "llm", "gpt", "openai", "google", "model", "models",
    "agent", "agents", "data", "training", "inference", "safety",
    "alignment", "benchmark", "api", "chatbot", "chatbots",
    "generative", "transformer", "reasoning", "coding",
    "multimodal", "vision", "language", "deepmind", "anthropic",
    "claude", "gemini", "image", "video", "search",
}


@dataclass(frozen=True)
class SourceBrief:
    source_id: str
    title: str
    url: str
    summary: str
    published_at: Optional[datetime]
    authority_weight: int

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "authority_weight": self.authority_weight,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SourceBrief":
        published_at = data.get("published_at")
        return cls(
            source_id=data["source_id"],
            title=data["title"],
            url=data["url"],
            summary=data["summary"],
            published_at=datetime.fromisoformat(published_at) if published_at else None,
            authority_weight=data["authority_weight"],
        )


@dataclass(frozen=True)
class TimelineEntry:
    source_id: str
    title: str
    published_at: Optional[datetime]

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimelineEntry":
        published_at = data.get("published_at")
        return cls(
            source_id=data["source_id"],
            title=data["title"],
            published_at=datetime.fromisoformat(published_at) if published_at else None,
        )


@dataclass(frozen=True)
class ResearchPacket:
    cluster_id: str
    headline: str
    event_summary: str
    primary_source_summary: str
    source_briefs: List[SourceBrief]
    timeline: List[TimelineEntry]
    keywords: List[str]
    open_questions: List[str]

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "headline": self.headline,
            "event_summary": self.event_summary,
            "primary_source_summary": self.primary_source_summary,
            "source_briefs": [b.to_dict() for b in self.source_briefs],
            "timeline": [t.to_dict() for t in self.timeline],
            "keywords": list(self.keywords),
            "open_questions": list(self.open_questions),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchPacket":
        return cls(
            cluster_id=data["cluster_id"],
            headline=data["headline"],
            event_summary=data["event_summary"],
            primary_source_summary=data["primary_source_summary"],
            source_briefs=[SourceBrief.from_dict(b) for b in data["source_briefs"]],
            timeline=[TimelineEntry.from_dict(t) for t in data["timeline"]],
            keywords=data["keywords"],
            open_questions=data["open_questions"],
        )


class ResearchService:
    def build_packet(self, cluster: EventCluster) -> ResearchPacket:
        source_briefs = [
            SourceBrief(
                source_id=document.source_id,
                title=html.unescape(document.title).strip(),
                url=document.url,
                summary=html.unescape(document.summary or "").strip(),
                published_at=document.published_at,
                authority_weight=document.authority_weight,
            )
            for document in cluster.documents
        ]
        primary_source = max(source_briefs, key=lambda brief: brief.authority_weight)
        timeline = sorted(
            [
                TimelineEntry(
                    source_id=brief.source_id,
                    title=brief.title,
                    published_at=brief.published_at,
                )
                for brief in source_briefs
            ],
            key=lambda entry: entry.published_at or datetime.max.replace(tzinfo=timezone.utc),
        )

        open_questions = self._collect_open_questions(source_briefs)
        keywords = self._extract_keywords(cluster.headline, source_briefs)
        event_summary = self._build_event_summary(cluster.headline, source_briefs)

        return ResearchPacket(
            cluster_id=cluster.cluster_id,
            headline=cluster.headline,
            event_summary=event_summary,
            primary_source_summary=primary_source.summary,
            source_briefs=source_briefs,
            timeline=timeline,
            keywords=keywords,
            open_questions=open_questions,
        )

    def _collect_open_questions(self, source_briefs: List[SourceBrief]) -> List[str]:
        questions: List[str] = []
        if len(source_briefs) == 1:
            questions.append("该事件目前仅有单一信源报道，建议关注更多独立媒体的跟进")
        if any(brief.published_at is None for brief in source_briefs):
            questions.append("部分消息源发布时间未知，难以判断时效性")
        if len(source_briefs) <= 2:
            questions.append("该事件覆盖度偏低，可能尚未引起广泛关注")
        # Check for competing claims
        titles = [b.title.lower() for b in source_briefs]
        if len(titles) >= 2 and len(set(titles)) < len(titles):
            questions.append("标题存在高度重复，需核实是否为同一新闻的不同转载")
        return questions

    def _extract_keywords(self, headline: str, source_briefs: List[SourceBrief]) -> List[str]:
        """Extract domain-relevant keywords from titles and headline."""
        all_text = " ".join([headline] + [brief.title for brief in source_briefs])

        # Chinese tokens first (more relevant for target audience)
        chinese_tokens = CHINESE_TOKEN_PATTERN.findall(all_text)
        # English tokens filtered by AI domain relevance
        english_tokens = TOKEN_PATTERN.findall(all_text)
        ai_tokens = [t for t in english_tokens if t.lower() in AI_DOMAIN_KEYWORDS]
        other_tokens = [
            t for t in english_tokens
            if t.lower() not in AI_DOMAIN_KEYWORDS and t.lower() not in STOP_WORDS
        ]

        result: List[str] = []
        seen: set = set()
        for token in chinese_tokens:
            if token.lower() in seen:
                continue
            seen.add(token.lower())
            result.append(token)
        for token in ai_tokens:
            if token.lower() in seen:
                continue
            seen.add(token.lower())
            result.append(token)
        for token in other_tokens:
            if len(result) >= 6:
                break
            if token.lower() in seen:
                continue
            seen.add(token.lower())
            result.append(token)
        return result[:6]

    def _build_event_summary(self, headline: str, source_briefs: List[SourceBrief]) -> str:
        """Build a meaningful event summary by combining source summaries."""
        source_count = len(source_briefs)
        summaries: List[str] = []
        for brief in source_briefs[:3]:
            clean = html.unescape(brief.summary or "").strip()
            if clean:
                # Take first 2 sentences max from each source
                sentences = re.split(r"(?<=[.!?。！？])\s+", clean)
                snippet = " ".join(sentences[:2]).strip()
                if len(snippet) > 200:
                    snippet = snippet[:200].rsplit(" ", 1)[0] + "..."
                summaries.append(snippet)

        if not summaries:
            return f"{headline}。目前共有 {source_count} 个相关报道来源。"

        combined = " ".join(summaries)
        return f"{headline}。该事件共有 {source_count} 个信源报道：{combined}"


class AgentResearchService:
    def __init__(
        self,
        provider: AgentProvider,
        fallback: ResearchService | None = None,
    ) -> None:
        self.provider = provider
        self.fallback = fallback or ResearchService()

    def build_packet(self, cluster: EventCluster) -> ResearchPacket:
        fallback_packet = self.fallback.build_packet(cluster)
        request = AgentRequest(
            task_name="research",
            prompt=self._build_prompt(fallback_packet),
            metadata={"cluster_id": cluster.cluster_id},
            response_schema=self._response_schema(),
        )
        try:
            response = self.provider.generate(request)
            raw = json.loads(response.output_text)
            # Handle case where parse_result returned the full Claude envelope
            if isinstance(raw, dict) and "structured_output" in raw:
                raw = raw["structured_output"]
            payload = ResearchAgentOutput.model_validate(raw)
            return ResearchPacket(
                cluster_id=fallback_packet.cluster_id,
                headline=fallback_packet.headline,
                event_summary=payload.event_summary,
                primary_source_summary=payload.primary_source_summary,
                source_briefs=fallback_packet.source_briefs,
                timeline=fallback_packet.timeline,
                keywords=payload.keywords,
                open_questions=payload.open_questions,
            )
        except Exception:
            logger.warning("Agent research failed, falling back to rule-based", exc_info=True)
            return fallback_packet

    @staticmethod
    def _build_prompt(packet: ResearchPacket) -> str:
        return json.dumps(
            {
                "instructions": (
                    "You are an AI industry research analyst. Given the following event cluster data, "
                    "produce a structured research summary:\n"
                    "- event_summary: A concise 2-3 sentence summary of what happened.\n"
                    "- primary_source_summary: The key takeaway from the most authoritative source.\n"
                    "- keywords: 3-6 relevant technical or industry keywords.\n"
                    "- open_questions: Important questions that remain unanswered.\n"
                    "Output must be valid JSON matching the response schema."
                ),
                "data": {
                    "headline": packet.headline,
                    "event_summary": packet.event_summary,
                    "primary_source_summary": packet.primary_source_summary,
                    "source_briefs": [
                        {
                            "source_id": brief.source_id,
                            "title": brief.title,
                            "summary": brief.summary,
                            "authority_weight": brief.authority_weight,
                        }
                        for brief in packet.source_briefs
                    ],
                    "timeline": [
                        {
                            "source_id": entry.source_id,
                            "title": entry.title,
                            "published_at": entry.published_at.isoformat() if entry.published_at else None,
                        }
                        for entry in packet.timeline
                    ],
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
                "event_summary": {"type": "string"},
                "primary_source_summary": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "open_questions": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "event_summary",
                "primary_source_summary",
                "keywords",
                "open_questions",
            ],
        }
