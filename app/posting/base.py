from __future__ import annotations

from typing import Protocol

from app.posting.models import Post
from app.services.research.service import ResearchPacket
from app.services.writing.service import DraftPackage


class PlatformPipeline(Protocol):
    @property
    def platform(self) -> str:
        ...

    def build_post(self, packet: ResearchPacket, draft: DraftPackage, job_id: str) -> Post:
        ...
