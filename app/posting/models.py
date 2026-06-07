from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Post:
    post_id: str
    job_id: str
    platform: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    status: str = "draft"
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "job_id": self.job_id,
            "platform": self.platform,
            "title": self.title,
            "body": self.body,
            "tags": list(self.tags),
            "status": self.status,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "url": self.url,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Post":
        published_at = data.get("published_at")
        created_at = data.get("created_at")
        return cls(
            post_id=data["post_id"],
            job_id=data["job_id"],
            platform=data["platform"],
            title=data["title"],
            body=data["body"],
            tags=data.get("tags", []),
            status=data.get("status", "draft"),
            published_at=datetime.fromisoformat(published_at) if published_at else None,
            url=data.get("url"),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(timezone.utc),
        )
