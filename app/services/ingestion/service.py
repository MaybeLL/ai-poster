from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List

import httpx

from app.core.settings import AppSettings
from app.services.ingestion.rss_adapter import RawDocument, RssIngestionAdapter
from app.services.ingestion.source_catalog import SourceCatalog


@dataclass(frozen=True)
class SourceIngestionError:
    source_id: str
    message: str

    def to_dict(self) -> dict:
        return {"source_id": self.source_id, "message": self.message}

    @classmethod
    def from_dict(cls, data: dict) -> "SourceIngestionError":
        return cls(source_id=data["source_id"], message=data["message"])


@dataclass(frozen=True)
class IngestionResult:
    documents: List[RawDocument] = field(default_factory=list)
    source_errors: List[SourceIngestionError] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "documents": [d.to_dict() for d in self.documents],
            "source_errors": [e.to_dict() for e in self.source_errors],
        }


class IngestionService:
    def __init__(
        self,
        settings: AppSettings,
        fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self.settings = settings
        self.fetcher = fetcher or self._default_fetcher

    def ingest_recent_documents(self, now: datetime, lookback_hours: int) -> List[RawDocument]:
        return self.ingest_recent_documents_with_errors(
            now=now,
            lookback_hours=lookback_hours,
        ).documents

    def ingest_recent_documents_with_errors(
        self,
        now: datetime,
        lookback_hours: int,
    ) -> IngestionResult:
        catalog = SourceCatalog.load(self.settings.resolve_sources_file())
        documents: List[RawDocument] = []
        source_errors: List[SourceIngestionError] = []

        for source in catalog.sources:
            if source.kind != "rss":
                raise ValueError(f"unsupported source kind: {source.kind}")

            adapter = RssIngestionAdapter(fetcher=self.fetcher)
            try:
                documents.extend(
                    adapter.fetch_recent_documents(
                        source=source,
                        now=now,
                        lookback_hours=lookback_hours,
                    )
                )
            except Exception as exc:
                source_errors.append(
                    SourceIngestionError(
                        source_id=source.source_id,
                        message=str(exc),
                    )
                )

        return IngestionResult(
            documents=documents,
            source_errors=source_errors,
        )

    @staticmethod
    def _default_fetcher(url: str) -> str:
        response = httpx.get(url, headers={"User-Agent": "ai-poster/0.1"}, timeout=20.0)
        response.raise_for_status()
        return response.text
