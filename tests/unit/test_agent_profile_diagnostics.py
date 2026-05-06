import json
import unittest

from app.agents.profiles import ClaudePrintProfile, CodexExecProfile
from app.agents.provider import AgentRequest, ProviderExecutionResult


class AgentProfileDiagnosticsTest(unittest.TestCase):
    def test_codex_profile_adds_ephemeral_flag_when_missing(self) -> None:
        profile = CodexExecProfile(base_command=["codex", "exec"])
        request = AgentRequest(task_name="smoke", prompt="hello", response_schema={"type": "object"})

        invocation = profile.build_invocation(request=request, scratch_dir=__import__("pathlib").Path("/tmp"))

        self.assertIn("--ephemeral", invocation.command)

    def test_claude_profile_reports_raw_output_when_json_parse_fails(self) -> None:
        profile = ClaudePrintProfile(base_command=["claude"])
        result = ProviderExecutionResult(stdout="Authentication required", stderr="", returncode=0)

        with self.assertRaises(ValueError) as context:
            profile.parse_result(result=result, invocation=None)

        self.assertIn("Authentication required", str(context.exception))


if __name__ == "__main__":
    unittest.main()
