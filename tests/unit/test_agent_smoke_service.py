import json
import tempfile
import unittest
from pathlib import Path

from app.agents.smoke import run_agent_smoke
from app.agents.provider import AgentInvocation, ProviderExecutionResult
from app.core.settings import AppSettings


class AgentSmokeServiceTest(unittest.TestCase):
    def test_rule_backend_skips_smoke_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = AppSettings(environment="test", data_dir=Path(temp_dir), intelligence_backend="rule")

            result = run_agent_smoke(settings=settings)

        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.backend, "rule")

    def test_codex_backend_reports_success_when_provider_returns_valid_json(self) -> None:
        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            Path(invocation.output_file).write_text(
                json.dumps({"status": "ok", "backend": "codex", "echo": "smoke"}),
                encoding="utf-8",
            )
            return ProviderExecutionResult(stdout="", stderr="", returncode=0)

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = AppSettings(
                environment="test",
                data_dir=Path(temp_dir),
                intelligence_backend="codex",
                codex_command=["codex", "exec"],
            )

            result = run_agent_smoke(settings=settings, executor=executor)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.backend, "codex")
        self.assertEqual(result.payload["status"], "ok")

    def test_claude_backend_reports_failure_when_provider_raises(self) -> None:
        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            return ProviderExecutionResult(stdout="", stderr="auth failed", returncode=1)

        with tempfile.TemporaryDirectory() as temp_dir:
            settings = AppSettings(
                environment="test",
                data_dir=Path(temp_dir),
                intelligence_backend="claude-code",
                claude_code_command=["claude"],
            )

            result = run_agent_smoke(settings=settings, executor=executor)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.backend, "claude-code")
        self.assertIn("auth failed", result.error_message)


if __name__ == "__main__":
    unittest.main()
