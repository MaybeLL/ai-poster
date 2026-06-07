from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.core.settings import AppSettings


def load_dotenv_if_exists(env_file: str | Path | None = None) -> None:
    if env_file is not None:
        load_dotenv(dotenv_path=str(env_file), override=False)
    else:
        load_dotenv(override=False)


_SETTINGS_CLI_MAP: dict[str, str] = {
    "data_dir": "data_dir",
    "database_url": "database_url",
    "database_echo": "database_echo",
    "api_host": "api_host",
    "api_port": "api_port",
    "intelligence_backend": "intelligence_backend",
    "telegram_bot_token": "telegram_bot_token",
    "telegram_chat_id": "telegram_chat_id",
}


def build_settings_from_cli(env_file: str | Path | None = None, **overrides: Any) -> AppSettings:
    load_dotenv_if_exists(env_file)
    base = AppSettings.from_env()
    filtered = {_SETTINGS_CLI_MAP[k]: v for k, v in overrides.items() if k in _SETTINGS_CLI_MAP and v is not None}
    if filtered:
        return base.apply_overrides(**filtered)
    return base
