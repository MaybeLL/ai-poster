from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from app.agents.factory import build_agent_provider
from app.agents.provider import AgentInvocation, AgentRequest, ProviderExecutionResult
from app.core.settings import AppSettings


@dataclass(frozen=True)
class AgentSmokeResult:
    backend: str
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


def run_agent_smoke(
    settings: AppSettings,
    executor: Callable[[AgentInvocation], ProviderExecutionResult] | None = None,
) -> AgentSmokeResult:
    provider = build_agent_provider(settings=settings, executor=executor)
    if provider is None:
        return AgentSmokeResult(
            backend="rule",
            status="skipped",
            error_message="rule backend does not launch an external agent process",
        )

    request = AgentRequest(
        task_name="smoke",
        prompt="Return a JSON object confirming the backend is reachable.",
        metadata={"purpose": "agent_smoke_test"},
        response_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "backend": {"type": "string"},
                "echo": {"type": "string"},
            },
            "required": ["status", "backend", "echo"],
        },
    )

    try:
        response = provider.generate(request)
        payload = json.loads(response.output_text)
        return AgentSmokeResult(
            backend=settings.intelligence_backend,
            status="success",
            payload=payload,
        )
    except Exception as exc:
        return AgentSmokeResult(
            backend=settings.intelligence_backend,
            status="failed",
            error_message=str(exc),
        )
