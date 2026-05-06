import json
import tempfile
import unittest
from pathlib import Path

from app.agents.provider import AgentInvocation, ProviderExecutionResult
from app.core.settings import AppSettings
from app.main import build_agent_smoke_summary


class AgentSmokeCliTest(unittest.TestCase):
    def test_summary_reports_successful_smoke(self) -> None:
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

            summary = build_agent_smoke_summary(settings=settings, executor=executor)

        self.assertIn("smoke_status: success", summary)
        self.assertIn("backend: codex", summary)
        self.assertIn("payload_status: ok", summary)


if __name__ == "__main__":
    unittest.main()
