from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agents.factory import build_agent_provider
from app.agents.provider import AgentInvocation, ProviderExecutionResult
from app.core.settings import AppSettings
from app.posting.pipelines.wechat import WeChatPostPipeline
from app.posting.pipelines.xiaohongshu import XiaohongshuPostPipeline
from app.posting.service import PostingService
from app.services.qa.service import AgentQaService, QaService
from app.services.research.service import AgentResearchService, ResearchService
from app.services.writing.service import AgentWritingService, WritingService


@dataclass(frozen=True)
class ContentServices:
    research_service: ResearchService | AgentResearchService
    writing_service: WritingService | AgentWritingService
    qa_service: QaService | AgentQaService
    posting_service: PostingService


def build_content_services(
    settings: AppSettings,
    executor: Callable[[AgentInvocation], ProviderExecutionResult] | None = None,
) -> ContentServices:
    provider = build_agent_provider(settings=settings, executor=executor)
    research_service = ResearchService()

    if provider is None:
        research = research_service
        writing = WritingService()
        qa = QaService()
    else:
        research = AgentResearchService(provider=provider, fallback=research_service)
        writing = AgentWritingService(provider=provider, fallback=WritingService())
        qa = AgentQaService(provider=provider, fallback=QaService())

    posting_service = PostingService(
        pipelines={
            "wechat": WeChatPostPipeline(provider=provider),
            "xiaohongshu": XiaohongshuPostPipeline(provider=provider),
        }
    )

    return ContentServices(
        research_service=research,
        writing_service=writing,
        qa_service=qa,
        posting_service=posting_service,
    )
