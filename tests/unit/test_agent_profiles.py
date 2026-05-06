import json
import tempfile
import unittest
from pathlib import Path

from app.agents.provider import AgentRequest, ProviderExecutionResult
from app.agents.profiles import ClaudePrintProfile, CodexExecProfile


class CodexExecProfileTest(unittest.TestCase):
    def test_build_invocation_writes_schema_and_reads_output_file(self) -> None:
        request = AgentRequest(
            task_name="writing",
            prompt="Return structured JSON",
            response_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        )
        profile = CodexExecProfile(base_command=["codex", "exec"])

        with tempfile.TemporaryDirectory() as temp_dir:
            invocation = profile.build_invocation(request=request, scratch_dir=Path(temp_dir))
            output_file = Path(invocation.output_file)
            output_file.write_text('{"value":"ok"}', encoding="utf-8")

            parsed = profile.parse_result(
                result=ProviderExecutionResult(stdout="", stderr="", returncode=0),
                invocation=invocation,
            )

        self.assertEqual(invocation.command[:2], ["codex", "exec"])
        self.assertIn("--output-schema", invocation.command)
        self.assertEqual(invocation.stdin_text, "Return structured JSON")
        self.assertEqual(parsed, '{"value":"ok"}')


class ClaudePrintProfileTest(unittest.TestCase):
    def test_build_invocation_passes_prompt_as_argument(self) -> None:
        request = AgentRequest(
            task_name="review",
            prompt="Review this draft",
            response_schema={
                "type": "object",
                "properties": {"score": {"type": "number"}},
                "required": ["score"],
            },
        )
        profile = ClaudePrintProfile(base_command=["claude"])

        with tempfile.TemporaryDirectory() as temp_dir:
            invocation = profile.build_invocation(request=request, scratch_dir=Path(temp_dir))

        self.assertEqual(invocation.command[:6], ["claude", "-p", "--output-format", "json", "--bare", "--no-session-persistence"])
        self.assertEqual(invocation.command[-1], "Review this draft")
        self.assertIsNone(invocation.stdin_text)

    def test_parse_result_accepts_raw_json_object(self) -> None:
        profile = ClaudePrintProfile(base_command=["claude"])
        result = ProviderExecutionResult(stdout='{"score":88}', stderr="", returncode=0)

        parsed = profile.parse_result(result=result, invocation=None)

        self.assertEqual(parsed, '{"score": 88}')

    def test_parse_result_extracts_json_from_wrapper(self) -> None:
        profile = ClaudePrintProfile(base_command=["claude"])
        result = ProviderExecutionResult(
            stdout=json.dumps({"result": '{"score": 88, "notes": []}'}),
            stderr="",
            returncode=0,
        )

        parsed = profile.parse_result(result=result, invocation=None)

        self.assertEqual(parsed, '{"score": 88, "notes": []}')

    def test_parse_result_reports_stderr_when_stdout_is_empty(self) -> None:
        profile = ClaudePrintProfile(base_command=["claude"])
        result = ProviderExecutionResult(stdout="", stderr="authentication required", returncode=0)

        with self.assertRaises(ValueError) as context:
            profile.parse_result(result=result, invocation=None)

        self.assertIn("authentication required", str(context.exception))


if __name__ == "__main__":
    unittest.main()
