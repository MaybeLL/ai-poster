import os
import unittest

from app.agents.factory import build_agent_provider
from app.core.settings import AppSettings


class AgentFactoryTest(unittest.TestCase):
    def test_returns_none_when_backend_is_rule(self) -> None:
        settings = AppSettings(environment="test", data_dir=None, intelligence_backend="rule")

        provider = build_agent_provider(settings)

        self.assertIsNone(provider)

    def test_builds_codex_provider_with_configured_command(self) -> None:
        settings = AppSettings(
            environment="test",
            data_dir=None,
            intelligence_backend="codex",
            codex_command=["codex", "exec", "--json"],
            claude_code_command=["claude-code"],
        )

        provider = build_agent_provider(settings)

        self.assertEqual(provider.provider_name, "codex")
        self.assertEqual(provider.command, ["codex", "exec", "--json"])

    def test_builds_claude_code_provider_with_default_command(self) -> None:
        settings = AppSettings(
            environment="test",
            data_dir=None,
            intelligence_backend="claude-code",
        )

        provider = build_agent_provider(settings)

        self.assertEqual(provider.provider_name, "claude-code")
        self.assertEqual(provider.command, ["claude"])


if __name__ == "__main__":
    unittest.main()
