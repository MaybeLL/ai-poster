import json
import unittest

from click.testing import CliRunner

from app.cli.main import main


class CliMainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_help(self) -> None:
        result = self.runner.invoke(main, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("AI Poster", result.output)

    def test_version(self) -> None:
        result = self.runner.invoke(main, ["--version"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("0.1.0", result.output)


class DemoCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_demo_default_topic(self) -> None:
        result = self.runner.invoke(main, ["demo"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("final_status: accepted", result.output)

    def test_demo_custom_topic(self) -> None:
        result = self.runner.invoke(main, ["demo", "--topic", "Custom topic"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("topic: Custom topic", result.output)

    def test_demo_json_output(self) -> None:
        result = self.runner.invoke(main, ["--json", "demo", "--topic", "JSON"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertEqual(data["topic"], "JSON")
        self.assertEqual(data["final_status"], "accepted")


class AgentCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_agent_help(self) -> None:
        result = self.runner.invoke(main, ["agent", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("probe", result.output)
        self.assertIn("smoke", result.output)

    def test_agent_probe(self) -> None:
        # Override .env so test sees default "rule" backend
        result = self.runner.invoke(main, ["agent", "probe"],
            env={"AI_POSTER_INTELLIGENCE_BACKEND": "rule"})
        self.assertEqual(result.exit_code, 0)
        self.assertIn("backend: rule", result.output)

    def test_agent_probe_json(self) -> None:
        result = self.runner.invoke(main, ["--json", "agent", "probe"],
            env={"AI_POSTER_INTELLIGENCE_BACKEND": "rule"})
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIn("backend", data)
        self.assertEqual(data["backend"], "rule")

    def test_agent_smoke(self) -> None:
        result = self.runner.invoke(main, ["agent", "smoke"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("smoke_status:", result.output)


class IngestCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_ingest(self) -> None:
        result = self.runner.invoke(main, ["ingest", "--lookback-hours", "1"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("environment:", result.output)

    def test_ingest_json(self) -> None:
        result = self.runner.invoke(main, ["--json", "ingest", "--lookback-hours", "1"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIn("document_count", data)


class EventsCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_events(self) -> None:
        result = self.runner.invoke(main, ["events", "--lookback-hours", "1", "--limit", "1"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("environment:", result.output)

    def test_events_json(self) -> None:
        result = self.runner.invoke(main, ["--json", "events", "--lookback-hours", "1", "--limit", "1"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIn("cluster_count", data)


class ResearchCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_research(self) -> None:
        result = self.runner.invoke(main, ["research", "--lookback-hours", "1", "--limit", "1"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("environment:", result.output)

    def test_research_json(self) -> None:
        result = self.runner.invoke(main, ["--json", "research", "--lookback-hours", "1", "--limit", "1"])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output)
        self.assertIn("packet_count", data)


class MigrateCommandTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_migrate_help(self) -> None:
        result = self.runner.invoke(main, ["migrate", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("upgrade", result.output)
        self.assertIn("downgrade", result.output)

    def test_migrate_current(self) -> None:
        result = self.runner.invoke(main, ["migrate", "current"])
        self.assertEqual(result.exit_code, 0)

    def test_migrate_history(self) -> None:
        result = self.runner.invoke(main, ["migrate", "history"])
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
