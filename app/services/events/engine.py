from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List

from app.services.ingestion.rss_adapter import RawDocument


TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


@dataclass(frozen=True)
class EventScore:
    freshness_score: float
    authority_score: float
    coverage_score: float
    total_score: float

    def to_dict(self) -> dict:
        return {
            "freshness_score": self.freshness_score,
            "authority_score": self.authority_score,
            "coverage_score": self.coverage_score,
            "total_score": self.total_score,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventScore":
        return cls(
            freshness_score=data["freshness_score"],
            authority_score=data["authority_score"],
            coverage_score=data["coverage_score"],
            total_score=data["total_score"],
        )


@dataclass(frozen=True)
class EventCluster:
    cluster_id: str
    headline: str
    documents: List[RawDocument]
    score: EventScore

    @property
    def document_count(self) -> int:
        return len(self.documents)

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "headline": self.headline,
            "documents": [d.to_dict() for d in self.documents],
            "score": self.score.to_dict(),
            "document_count": self.document_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EventCluster":
        return cls(
            cluster_id=data["cluster_id"],
            headline=data["headline"],
            documents=[RawDocument.from_dict(d) for d in data["documents"]],
            score=EventScore.from_dict(data["score"]),
        )


class EventEngine:
    def cluster_documents(self, documents: Iterable[RawDocument]) -> List[EventCluster]:
        clusters: List[list[RawDocument]] = []

        for document in documents:
            matched_cluster = self._find_matching_cluster(clusters, document)
            if matched_cluster is None:
                clusters.append([document])
            else:
                matched_cluster.append(document)

        return [
            EventCluster(
                cluster_id=f"cluster-{index + 1}",
                headline=self._select_headline(cluster_documents),
                documents=sorted(
                    cluster_documents,
                    key=lambda item: (
                        item.published_at or datetime.min.replace(tzinfo=timezone.utc),
                        item.authority_weight,
                    ),
                    reverse=True,
                ),
                score=EventScore(
                    freshness_score=0.0,
                    authority_score=0.0,
                    coverage_score=0.0,
                    total_score=0.0,
                ),
            )
            for index, cluster_documents in enumerate(clusters)
        ]

    def rank_clusters(self, clusters: Iterable[EventCluster], now: datetime) -> List[EventCluster]:
        ranked_clusters: List[EventCluster] = []
        for cluster in clusters:
            freshness_score = self._compute_freshness_score(cluster.documents, now)
            authority_score = max(document.authority_weight for document in cluster.documents) * 5
            coverage_score = min(cluster.document_count, 5) * 4
            total_score = round(freshness_score + authority_score + coverage_score, 2)
            ranked_clusters.append(
                EventCluster(
                    cluster_id=cluster.cluster_id,
                    headline=cluster.headline,
                    documents=cluster.documents,
                    score=EventScore(
                        freshness_score=round(freshness_score, 2),
                        authority_score=round(authority_score, 2),
                        coverage_score=round(coverage_score, 2),
                        total_score=total_score,
                    ),
                )
            )

        return sorted(ranked_clusters, key=lambda cluster: cluster.score.total_score, reverse=True)

    def select_top_clusters(
        self,
        documents: Iterable[RawDocument],
        now: datetime,
        limit: int,
    ) -> List[EventCluster]:
        clustered = self.cluster_documents(documents)
        ranked = self.rank_clusters(clustered, now=now)
        return ranked[:limit]

    def _find_matching_cluster(
        self,
        clusters: List[list[RawDocument]],
        document: RawDocument,
    ) -> list[RawDocument] | None:
        for cluster in clusters:
            if self._titles_are_similar(cluster[0].title, document.title):
                return cluster
        return None

    def _titles_are_similar(self, left: str, right: str) -> bool:
        left_tokens = self._normalize_tokens(left)
        right_tokens = self._normalize_tokens(right)
        if not left_tokens or not right_tokens:
            return False
        overlap = len(left_tokens & right_tokens)
        union = len(left_tokens | right_tokens)
        return (overlap / union) >= 0.6

    def _normalize_tokens(self, value: str) -> set[str]:
        return set(TOKEN_PATTERN.findall(value.lower()))

    def _select_headline(self, documents: list[RawDocument]) -> str:
        ranked_documents = sorted(
            documents,
            key=lambda item: (item.authority_weight, len(item.title)),
            reverse=True,
        )
        return ranked_documents[0].title

    def _compute_freshness_score(self, documents: list[RawDocument], now: datetime) -> float:
        timestamps = [document.published_at for document in documents if document.published_at is not None]
        if not timestamps:
            return 10.0

        most_recent = max(timestamps)
        age_hours = max((now - most_recent).total_seconds() / 3600, 0)
        return max(0.0, 30.0 - min(age_hours, 24.0) * 1.25)
