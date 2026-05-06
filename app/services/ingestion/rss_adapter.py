from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, List, Optional
from xml.etree import ElementTree

from app.services.ingestion.source_catalog import SourceDefinition


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    title: str
    url: str
    summary: str
    published_at: Optional[datetime]
    authority_weight: int

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "authority_weight": self.authority_weight,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RawDocument":
        published_at = data.get("published_at")
        return cls(
            source_id=data["source_id"],
            title=data["title"],
            url=data["url"],
            summary=data["summary"],
            published_at=datetime.fromisoformat(published_at) if published_at else None,
            authority_weight=data["authority_weight"],
        )


class RssIngestionAdapter:
    def __init__(self, fetcher: Callable[[str], str]) -> None:
        self.fetcher = fetcher

    def fetch_recent_documents(
        self,
        source: SourceDefinition,
        now: datetime,
        lookback_hours: int,
    ) -> List[RawDocument]:
        xml = self.fetcher(source.url)
        root = ElementTree.fromstring(xml)
        cutoff = now - timedelta(hours=lookback_hours)
        documents: List[RawDocument] = []

        for item in root.findall("./channel/item"):
            title = self._read_text(item, "title") or "Untitled item"
            url = self._read_text(item, "link") or source.url
            summary = self._read_text(item, "description") or ""
            published_at = self._parse_pub_date(self._read_text(item, "pubDate"))

            if published_at is not None and published_at < cutoff:
                continue

            documents.append(
                RawDocument(
                    source_id=source.source_id,
                    title=title,
                    url=url,
                    summary=summary,
                    published_at=published_at,
                    authority_weight=source.authority_weight,
                )
            )

        return documents

    @staticmethod
    def _read_text(item: ElementTree.Element, tag_name: str) -> Optional[str]:
        node = item.find(tag_name)
        if node is None or node.text is None:
            return None
        return node.text.strip()

    @staticmethod
    def _parse_pub_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
