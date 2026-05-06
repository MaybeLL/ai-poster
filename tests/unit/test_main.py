import unittest

from app.main import build_demo_summary


class MainEntryPointTest(unittest.TestCase):
    def test_build_demo_summary_reports_acceptance(self) -> None:
        summary = build_demo_summary("OpenAI releases a new coding model")

        self.assertIn("final_status: accepted", summary)
        self.assertIn("topic: OpenAI releases a new coding model", summary)
        self.assertIn("failed_checks: none", summary)


if __name__ == "__main__":
    unittest.main()
