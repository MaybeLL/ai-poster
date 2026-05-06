from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    name: str
    kind: str
    url: str
    authority_weight: int
    enabled: bool


@dataclass(frozen=True)
class SourceCatalog:
    sources: List[SourceDefinition]

    @classmethod
    def load(cls, path: Path) -> "SourceCatalog":
        payload = json.loads(path.read_text(encoding="utf-8"))
        sources: List[SourceDefinition] = []
        seen_source_ids = set()

        for item in payload.get("sources", []):
            source = SourceDefinition(
                source_id=item["source_id"],
                name=item["name"],
                kind=item["kind"],
                url=item["url"],
                authority_weight=item["authority_weight"],
                enabled=item["enabled"],
            )
            if source.source_id in seen_source_ids:
                raise ValueError(f"duplicate source_id: {source.source_id}")
            seen_source_ids.add(source.source_id)
            if source.enabled:
                sources.append(source)

        return cls(sources=sources)
