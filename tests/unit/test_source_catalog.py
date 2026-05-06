import json
import tempfile
import unittest
from pathlib import Path

from app.services.ingestion.source_catalog import SourceCatalog


class SourceCatalogTest(unittest.TestCase):
    def test_load_reads_enabled_sources_only(self) -> None:
        payload = {
            "sources": [
                {
                    "source_id": "openai-blog",
                    "name": "OpenAI Blog",
                    "kind": "rss",
                    "url": "https://openai.com/blog/rss.xml",
                    "enabled": True,
                    "authority_weight": 10,
                },
                {
                    "source_id": "disabled-source",
                    "name": "Disabled",
                    "kind": "rss",
                    "url": "https://example.com/rss.xml",
                    "enabled": False,
                    "authority_weight": 1,
                },
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sources.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            catalog = SourceCatalog.load(config_path)

        self.assertEqual(len(catalog.sources), 1)
        self.assertEqual(catalog.sources[0].source_id, "openai-blog")

    def test_load_rejects_duplicate_source_ids(self) -> None:
        payload = {
            "sources": [
                {
                    "source_id": "same-id",
                    "name": "One",
                    "kind": "rss",
                    "url": "https://example.com/one.xml",
                    "enabled": True,
                    "authority_weight": 10,
                },
                {
                    "source_id": "same-id",
                    "name": "Two",
                    "kind": "rss",
                    "url": "https://example.com/two.xml",
                    "enabled": True,
                    "authority_weight": 9,
                },
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sources.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValueError):
                SourceCatalog.load(config_path)


if __name__ == "__main__":
    unittest.main()
