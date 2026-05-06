from __future__ import annotations

import os
import shlex
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    environment: str
    data_dir: Path
    intelligence_backend: str = "rule"
    codex_command: list[str] = field(default_factory=lambda: ["codex", "exec"])
    claude_code_command: list[str] = field(default_factory=lambda: ["claude"])
    codex_env: dict[str, str] = field(default_factory=dict)
    claude_code_env: dict[str, str] = field(default_factory=dict)
    database_url: str = "sqlite:///data/ai_poster.db"
    database_echo: bool = False
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    @classmethod
    def from_env(cls) -> "AppSettings":
        environment = os.environ.get("AI_POSTER_ENV", "development")
        data_dir = Path(os.environ.get("AI_POSTER_DATA_DIR", "data"))
        intelligence_backend = os.environ.get("AI_POSTER_INTELLIGENCE_BACKEND", "rule")
        codex_command = _split_command(os.environ.get("AI_POSTER_CODEX_COMMAND"), ["codex", "exec"])
        claude_code_command = _split_command(
            os.environ.get("AI_POSTER_CLAUDE_CODE_COMMAND"),
            ["claude"],
        )
        codex_env = _parse_env_json(os.environ.get("AI_POSTER_CODEX_ENV_JSON"))
        claude_code_env = _parse_env_json(os.environ.get("AI_POSTER_CLAUDE_CODE_ENV_JSON"))
        database_url = os.environ.get("DATABASE_URL", "sqlite:///data/ai_poster.db")
        database_echo = os.environ.get("DATABASE_ECHO", "").lower() in ("1", "true", "yes")
        api_host = os.environ.get("AI_POSTER_API_HOST", "127.0.0.1")
        api_port = int(os.environ.get("AI_POSTER_API_PORT", "8000"))
        celery_broker_url = os.environ.get("AI_POSTER_CELERY_BROKER_URL", "redis://localhost:6379/0")
        celery_result_backend = os.environ.get("AI_POSTER_CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
        return cls(
            environment=environment,
            data_dir=data_dir,
            intelligence_backend=intelligence_backend,
            codex_command=codex_command,
            claude_code_command=claude_code_command,
            codex_env=codex_env,
            claude_code_env=claude_code_env,
            database_url=database_url,
            database_echo=database_echo,
            api_host=api_host,
            api_port=api_port,
            celery_broker_url=celery_broker_url,
            celery_result_backend=celery_result_backend,
        )

    def resolve_sources_file(self) -> Path:
        return self.data_dir / "sources.json"


def _split_command(raw_value: str | None, default: list[str]) -> list[str]:
    if not raw_value:
        return list(default)
    return shlex.split(raw_value)


def _parse_env_json(raw_value: str | None) -> dict[str, str]:
    if not raw_value:
        return {}
    parsed = json.loads(raw_value)
    return {str(key): str(value) for key, value in parsed.items()}
