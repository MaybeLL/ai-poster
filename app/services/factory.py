from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agents.factory import build_agent_provider
from app.agents.provider import AgentInvocation, ProviderExecutionResult
from app.core.settings import AppSettings
from app.services.qa.service import AgentQaService, QaService
from app.services.research.service import AgentResearchService, ResearchService
from app.services.writing.service import AgentWritingService, WritingService


@dataclass(frozen=True)
class ContentServices:
    research_service: ResearchService | AgentResearchService
    writing_service: WritingService | AgentWritingService
    qa_service: QaService | AgentQaService


def build_content_services(
    settings: AppSettings,
    executor: Callable[[AgentInvocation], ProviderExecutionResult] | None = None,
) -> ContentServices:
    provider = build_agent_provider(settings=settings, executor=executor)
    research_service = ResearchService()
    if provider is None:
        return ContentServices(
            research_service=research_service,
            writing_service=WritingService(),
            qa_service=QaService(),
        )

    return ContentServices(
        research_service=AgentResearchService(provider=provider, fallback=research_service),
        writing_service=AgentWritingService(provider=provider, fallback=WritingService()),
        qa_service=AgentQaService(provider=provider, fallback=QaService()),
    )
