from __future__ import annotations

from app.posting.base import PlatformPipeline
from app.posting.models import Post
from app.services.research.service import ResearchPacket


class PostingService:
    """Runs all registered platform pipelines against a research packet."""

    def __init__(self, pipelines: dict[str, PlatformPipeline]) -> None:
        self.pipelines = dict(pipelines)

    @property
    def platforms(self) -> list[str]:
        return list(self.pipelines.keys())

    def generate_posts(self, packet: ResearchPacket, job_id: str) -> list[Post]:
        return [
            pipeline.build_post(packet, job_id)
            for pipeline in self.pipelines.values()
        ]
