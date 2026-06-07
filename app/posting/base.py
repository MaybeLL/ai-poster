from __future__ import annotations

from typing import Protocol

from app.posting.models import Post
from app.services.research.service import ResearchPacket


class PlatformPipeline(Protocol):
    @property
    def platform(self) -> str:
        ...

    def build_post(self, packet: ResearchPacket, job_id: str) -> Post:
        ...
