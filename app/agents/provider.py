from __future__ import annotations

import subprocess
import tempfile
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Optional, Protocol


@dataclass(frozen=True)
class AgentRequest:
    task_name: str
    prompt: str
    metadata: Dict[str, str] = field(default_factory=dict)
    response_schema: dict | None = None


@dataclass(frozen=True)
class AgentResponse:
    provider_name: str
    output_text: str


@dataclass(frozen=True)
class ProviderExecutionResult:
    stdout: str
    stderr: str
    returncode: int


@dataclass(frozen=True)
class AgentInvocation:
    command: list[str]
    stdin_text: Optional[str] = None
    output_file: Optional[str] = None
    environment: Optional[Dict[str, str]] = None


class AgentProvider(Protocol):
    def generate(self, request: AgentRequest) -> AgentResponse:
        ...


class AgentProfile(Protocol):
    def build_invocation(self, request: AgentRequest, scratch_dir: Path) -> AgentInvocation:
        ...

    def parse_result(
        self,
        result: ProviderExecutionResult,
        invocation: AgentInvocation | None,
    ) -> str:
        ...


class ProcessAgentProvider:
    def __init__(
        self,
        provider_name: str,
        profile: AgentProfile,
        executor: Callable[[AgentInvocation], ProviderExecutionResult] | None = None,
        environment_overrides: Dict[str, str] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.profile = profile
        self.executor = executor or self._default_executor
        self.environment_overrides = environment_overrides or {}

    @property
    def command(self) -> list[str]:
        return list(getattr(self.profile, "base_command", []))

    def generate(self, request: AgentRequest) -> AgentResponse:
        with tempfile.TemporaryDirectory(prefix="ai-poster-agent-") as temp_dir:
            invocation = self.profile.build_invocation(request=request, scratch_dir=Path(temp_dir))
            if self.environment_overrides:
                invocation = AgentInvocation(
                    command=invocation.command,
                    stdin_text=invocation.stdin_text,
                    output_file=invocation.output_file,
                    environment=self.environment_overrides,
                )
            result = self.executor(invocation)
            if result.returncode != 0:
                raise RuntimeError(
                    f"{self.provider_name} process failed with exit code {result.returncode}: {result.stderr}"
                )
            output_text = self.profile.parse_result(result=result, invocation=invocation)
            return AgentResponse(
                provider_name=self.provider_name,
                output_text=output_text,
            )

    @staticmethod
    def _default_executor(invocation: AgentInvocation) -> ProviderExecutionResult:
        env = os.environ.copy()
        if invocation.environment:
            env.update(invocation.environment)
        completed = subprocess.run(
            invocation.command,
            input=invocation.stdin_text,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        return ProviderExecutionResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )
