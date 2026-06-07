from __future__ import annotations

from app.posting.base import PlatformPipeline
from app.posting.models import Post
from app.services.research.service import ResearchPacket
from app.services.writing.service import DraftPackage


class PostingService:
    """Runs all registered platform pipelines against a research packet and draft."""

    def __init__(self, pipelines: dict[str, PlatformPipeline]) -> None:
        self.pipelines = dict(pipelines)

    @property
    def platforms(self) -> list[str]:
        return list(self.pipelines.keys())

    def generate_posts(self, packet: ResearchPacket, draft: DraftPackage, job_id: str) -> list[Post]:
        return [
            pipeline.build_post(packet, draft, job_id)
            for pipeline in self.pipelines.values()
        ]
