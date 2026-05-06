from __future__ import annotations

from typing import Callable

from app.agents.profiles import ClaudePrintProfile, CodexExecProfile
from app.agents.provider import AgentInvocation, ProcessAgentProvider, ProviderExecutionResult
from app.core.settings import AppSettings


def build_agent_provider(
    settings: AppSettings,
    executor: Callable[[AgentInvocation], ProviderExecutionResult] | None = None,
) -> ProcessAgentProvider | None:
    if settings.intelligence_backend == "rule":
        return None

    if settings.intelligence_backend == "codex":
        return ProcessAgentProvider(
            provider_name="codex",
            profile=CodexExecProfile(base_command=settings.codex_command),
            executor=executor,
            environment_overrides=settings.codex_env,
        )

    if settings.intelligence_backend == "claude-code":
        return ProcessAgentProvider(
            provider_name="claude-code",
            profile=ClaudePrintProfile(base_command=settings.claude_code_command),
            executor=executor,
            environment_overrides=settings.claude_code_env,
        )

    raise ValueError(f"unsupported intelligence backend: {settings.intelligence_backend}")
