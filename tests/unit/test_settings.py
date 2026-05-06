import os
import tempfile
import unittest
from pathlib import Path

from app.core.settings import AppSettings


class AppSettingsTest(unittest.TestCase):
    def test_from_env_uses_defaults_when_vars_are_missing(self) -> None:
        previous = {key: os.environ.get(key) for key in ("AI_POSTER_ENV", "AI_POSTER_DATA_DIR")}
        for key in previous:
            os.environ.pop(key, None)

        try:
            settings = AppSettings.from_env()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.data_dir, Path("data"))

    def test_from_env_reads_custom_values(self) -> None:
        previous = {key: os.environ.get(key) for key in ("AI_POSTER_ENV", "AI_POSTER_DATA_DIR")}
        os.environ["AI_POSTER_ENV"] = "production"
        os.environ["AI_POSTER_DATA_DIR"] = "/tmp/ai-poster-data"

        try:
            settings = AppSettings.from_env()
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertEqual(settings.environment, "production")
        self.assertEqual(settings.data_dir, Path("/tmp/ai-poster-data"))

    def test_resolve_sources_file_uses_data_dir(self) -> None:
        settings = AppSettings(environment="development", data_dir=Path("/tmp/ai-poster"))

        self.assertEqual(
            settings.resolve_sources_file(),
            Path("/tmp/ai-poster") / "sources.json",
        )


if __name__ == "__main__":
    unittest.main()
