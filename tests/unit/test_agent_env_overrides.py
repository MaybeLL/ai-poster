import os
import unittest

from app.agents.provider import AgentInvocation, ProcessAgentProvider, ProviderExecutionResult
from app.agents.profiles import StdinJsonProfile
from app.agents.factory import build_agent_provider
from app.core.settings import AppSettings


class AgentEnvOverridesTest(unittest.TestCase):
    def test_process_provider_passes_environment_overrides_to_executor(self) -> None:
        captured = {}

        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            captured["environment"] = invocation.environment
            return ProviderExecutionResult(stdout='{"ok":true}', stderr="", returncode=0)

        provider = ProcessAgentProvider(
            provider_name="test",
            profile=StdinJsonProfile(base_command=["echo"]),
            executor=executor,
            environment_overrides={"CODEX_HOME": "/tmp/codex-home"},
        )

        provider.generate(__import__("app.agents.provider", fromlist=["AgentRequest"]).AgentRequest(task_name="x", prompt="y"))

        self.assertEqual(captured["environment"]["CODEX_HOME"], "/tmp/codex-home")

    def test_factory_builds_provider_with_backend_env_overrides(self) -> None:
        settings = AppSettings(
            environment="test",
            data_dir=None,
            intelligence_backend="codex",
            codex_command=["codex", "exec"],
            codex_env={"CODEX_HOME": "/tmp/codex-home"},
            claude_code_env={},
        )

        provider = build_agent_provider(settings=settings)

        self.assertEqual(provider.environment_overrides["CODEX_HOME"], "/tmp/codex-home")


if __name__ == "__main__":
    unittest.main()
