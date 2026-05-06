import json
import unittest

from app.agents.provider import (
    AgentRequest,
    AgentInvocation,
    ProcessAgentProvider,
    ProviderExecutionResult,
)
from app.agents.profiles import StdinJsonProfile


class ProcessAgentProviderTest(unittest.TestCase):
    def test_generate_uses_executor_and_returns_text(self) -> None:
        calls = []

        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            calls.append(invocation)
            return ProviderExecutionResult(stdout='{"message":"ok"}', stderr="", returncode=0)

        provider = ProcessAgentProvider(
            provider_name="codex",
            profile=StdinJsonProfile(base_command=["codex", "exec"]),
            executor=executor,
        )

        response = provider.generate(
            AgentRequest(
                task_name="writing",
                prompt="Produce JSON output",
                metadata={"cluster_id": "cluster-1"},
            )
        )

        self.assertEqual(response.provider_name, "codex")
        self.assertEqual(response.output_text, '{"message":"ok"}')
        self.assertEqual(calls[0].command, ["codex", "exec"])
        self.assertIn("Produce JSON output", calls[0].stdin_text)

    def test_generate_raises_when_process_fails(self) -> None:
        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            return ProviderExecutionResult(stdout="", stderr="boom", returncode=1)

        provider = ProcessAgentProvider(
            provider_name="claude-code",
            profile=StdinJsonProfile(base_command=["claude-code"]),
            executor=executor,
        )

        with self.assertRaises(RuntimeError):
            provider.generate(AgentRequest(task_name="review", prompt="Review draft"))


if __name__ == "__main__":
    unittest.main()
