import unittest

from app.core.settings import AppSettings
from app.services.factory import build_content_services
from app.services.qa.service import AgentQaService, QaService
from app.services.research.service import AgentResearchService, ResearchService
from app.services.writing.service import AgentWritingService, WritingService


class ContentFactoryTest(unittest.TestCase):
    def test_build_content_services_uses_rule_services_by_default(self) -> None:
        settings = AppSettings(environment="test", data_dir=None, intelligence_backend="rule")

        services = build_content_services(settings)

        self.assertIsInstance(services.research_service, ResearchService)
        self.assertIsInstance(services.writing_service, WritingService)
        self.assertIsInstance(services.qa_service, QaService)

    def test_build_content_services_wraps_agent_services_when_backend_selected(self) -> None:
        settings = AppSettings(
            environment="test",
            data_dir=None,
            intelligence_backend="codex",
            codex_command=["codex", "exec"],
            claude_code_command=["claude-code"],
        )

        services = build_content_services(settings, executor=lambda invocation: None)

        self.assertIsInstance(services.research_service, AgentResearchService)
        self.assertIsInstance(services.writing_service, AgentWritingService)
        self.assertIsInstance(services.qa_service, AgentQaService)


if __name__ == "__main__":
    unittest.main()
