import tempfile
import unittest
from pathlib import Path

from app.core.settings import AppSettings
from app.main import build_agent_probe_summary


class AgentProbeCliTest(unittest.TestCase):
    def test_probe_reports_selected_backend_and_command_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = AppSettings(
                environment="test",
                data_dir=Path(temp_dir),
                intelligence_backend="codex",
                codex_command=["codex", "exec"],
            )

            summary = build_agent_probe_summary(settings=settings, resolver=lambda command: f"/bin/{command}")

        self.assertIn("backend: codex", summary)
        self.assertIn("resolved_executable: /bin/codex", summary)


if __name__ == "__main__":
    unittest.main()
