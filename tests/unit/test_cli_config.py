import os
import tempfile
import unittest
from pathlib import Path

from app.cli.config import build_settings_from_cli, load_dotenv_if_exists
from app.core.settings import AppSettings


class LoadDotenvIfExistsTest(unittest.TestCase):
    def test_no_env_file_does_not_raise(self) -> None:
        load_dotenv_if_exists(env_file=None)

    def test_loads_dotenv_from_specified_path(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("AI_POSTER_ENV=staging\n")
            env_path = f.name

        try:
            prev = os.environ.get("AI_POSTER_ENV")
            os.environ.pop("AI_POSTER_ENV", None)
            load_dotenv_if_exists(env_file=env_path)
            self.assertEqual(os.environ.get("AI_POSTER_ENV"), "staging")
        finally:
            if prev is not None:
                os.environ["AI_POSTER_ENV"] = prev
            os.unlink(env_path)

    def test_dotenv_does_not_override_existing_env(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("AI_POSTER_ENV=from_dotenv\n")
            env_path = f.name

        try:
            os.environ["AI_POSTER_ENV"] = "from_process"
            load_dotenv_if_exists(env_file=env_path)
            self.assertEqual(os.environ.get("AI_POSTER_ENV"), "from_process")
        finally:
            os.unlink(env_path)


class BuildSettingsFromCliTest(unittest.TestCase):
    def test_returns_defaults_when_no_env_or_cli(self) -> None:
        to_clear = [
            "AI_POSTER_ENV",
            "AI_POSTER_DATA_DIR",
            "AI_POSTER_INTELLIGENCE_BACKEND",
            "AI_POSTER_TELEGRAM_BOT_TOKEN",
            "AI_POSTER_TELEGRAM_CHAT_ID",
        ]
        prev = {k: os.environ.get(k) for k in to_clear}
        for k in to_clear:
            os.environ.pop(k, None)

        try:
            # Use a non-existent env file so project .env is not loaded
            settings = build_settings_from_cli(env_file="/dev/null/nonexistent/.env")
            self.assertEqual(settings.environment, "development")
            self.assertEqual(settings.data_dir, Path("data"))
            self.assertEqual(settings.intelligence_backend, "rule")
        finally:
            for k, v in prev.items():
                if v is not None:
                    os.environ[k] = v

    def test_cli_overrides_win_over_env(self) -> None:
        prev = os.environ.get("AI_POSTER_ENV")
        os.environ["AI_POSTER_ENV"] = "production"
        try:
            settings = build_settings_from_cli()
            self.assertEqual(settings.environment, "production")
        finally:
            if prev is not None:
                os.environ["AI_POSTER_ENV"] = prev
            else:
                os.environ.pop("AI_POSTER_ENV", None)

    def test_cli_kwargs_override_settings(self) -> None:
        settings = build_settings_from_cli(database_url="sqlite:///custom.db")
        self.assertEqual(settings.database_url, "sqlite:///custom.db")

    def test_cli_none_kwargs_do_not_override(self) -> None:
        prev = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = "sqlite:///env.db"
        try:
            settings = build_settings_from_cli(database_url=None)
            self.assertEqual(settings.database_url, "sqlite:///env.db")
        finally:
            if prev is not None:
                os.environ["DATABASE_URL"] = prev
            else:
                os.environ.pop("DATABASE_URL", None)


class AppSettingsApplyOverridesTest(unittest.TestCase):
    def test_apply_overrides_creates_new_instance_with_updated_fields(self) -> None:
        original = AppSettings(environment="development", data_dir=Path("data"))
        updated = original.apply_overrides(environment="staging", telegram_bot_token="abc")
        self.assertEqual(updated.environment, "staging")
        self.assertEqual(updated.telegram_bot_token, "abc")
        self.assertEqual(updated.data_dir, Path("data"))

    def test_apply_overrides_does_not_mutate_original(self) -> None:
        original = AppSettings(environment="development", data_dir=Path("data"))
        original.apply_overrides(environment="staging")
        self.assertEqual(original.environment, "development")

    def test_apply_overrides_ignores_none_values(self) -> None:
        original = AppSettings(environment="production", data_dir=Path("data"))
        updated = original.apply_overrides(environment=None)
        self.assertEqual(updated.environment, "production")


if __name__ == "__main__":
    unittest.main()
