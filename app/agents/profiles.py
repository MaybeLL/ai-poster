from __future__ import annotations

import json
from pathlib import Path
from json import JSONDecodeError

from app.agents.provider import AgentInvocation, AgentRequest, ProviderExecutionResult


class StdinJsonProfile:
    def __init__(self, base_command: list[str]) -> None:
        self.base_command = base_command

    def build_invocation(self, request: AgentRequest, scratch_dir: Path) -> AgentInvocation:
        return AgentInvocation(command=list(self.base_command), stdin_text=self._build_prompt(request))

    def parse_result(self, result: ProviderExecutionResult, invocation: AgentInvocation | None) -> str:
        return result.stdout.strip()

    @staticmethod
    def _build_prompt(request: AgentRequest) -> str:
        metadata_lines = [f"{key}: {value}" for key, value in sorted(request.metadata.items())]
        metadata_block = "\n".join(metadata_lines)
        if metadata_block:
            return "\n\n".join((f"task: {request.task_name}", metadata_block, request.prompt))
        return "\n\n".join((f"task: {request.task_name}", request.prompt))


class CodexExecProfile:
    def __init__(self, base_command: list[str]) -> None:
        self.base_command = base_command

    def build_invocation(self, request: AgentRequest, scratch_dir: Path) -> AgentInvocation:
        schema_path = scratch_dir / f"{request.task_name}-schema.json"
        output_path = scratch_dir / f"{request.task_name}-output.json"
        schema_path.write_text(json.dumps(request.response_schema or {}, ensure_ascii=True), encoding="utf-8")
        command = list(self.base_command)
        if "--ephemeral" not in command:
            command.append("--ephemeral")
        command += [
            "-",
            "--skip-git-repo-check",
            "--output-schema",
            str(schema_path),
            "-o",
            str(output_path),
        ]
        return AgentInvocation(
            command=command,
            stdin_text=request.prompt,
            output_file=str(output_path),
        )

    def parse_result(self, result: ProviderExecutionResult, invocation: AgentInvocation | None) -> str:
        if invocation is None or invocation.output_file is None:
            raise ValueError("codex invocation missing output file")
        return Path(invocation.output_file).read_text(encoding="utf-8").strip()


class ClaudePrintProfile:
    def __init__(self, base_command: list[str]) -> None:
        self.base_command = base_command

    def build_invocation(self, request: AgentRequest, scratch_dir: Path) -> AgentInvocation:
        command = list(self.base_command) + [
            "-p",
            "--output-format",
            "json",
            "--bare",
            "--no-session-persistence",
        ]
        if request.response_schema is not None:
            command.extend(["--json-schema", json.dumps(request.response_schema, ensure_ascii=True)])
        command.append(request.prompt)
        return AgentInvocation(command=command)

    def parse_result(self, result: ProviderExecutionResult, invocation: AgentInvocation | None) -> str:
        raw = result.stdout.strip()
        try:
            parsed = json.loads(raw)
        except JSONDecodeError as exc:
            if raw:
                snippet = raw[:240]
            elif result.stderr.strip():
                snippet = f"<empty stdout; stderr: {result.stderr.strip()[:240]}>"
            else:
                snippet = "<empty stdout>"
            raise ValueError(f"claude output was not valid JSON: {snippet}") from exc

        if isinstance(parsed, dict) and "structured_output" in parsed:
            return json.dumps(parsed["structured_output"], ensure_ascii=True)

        if isinstance(parsed, dict) and "result" in parsed and isinstance(parsed["result"], str):
            inner = json.loads(parsed["result"])
            return json.dumps(inner, ensure_ascii=True)
        return json.dumps(parsed, ensure_ascii=True)
