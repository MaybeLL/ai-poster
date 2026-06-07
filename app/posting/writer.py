from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from app.posting.models import Post


def _slugify(text: str, max_len: int = 50) -> str:
    slug = re.sub(r"[^\w一-鿿]+", "_", text.strip()).strip("_")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("_")
    return slug.lower() if slug.isascii() else slug


def _frontmatter(post: Post) -> str:
    q = '"'
    lines = ["---"]
    lines.append(f'platform: "{post.platform}"')
    lines.append(f'title: "{post.title}"')
    lines.append(f"tags: [{', '.join(f'{q}{t}{q}' for t in post.tags)}]")
    lines.append(f"status: {post.status}")
    lines.append(f"created_at: {post.created_at.isoformat()}")
    lines.append(f"job_id: {post.job_id}")
    lines.append("---")
    return "\n".join(lines)


def write_post(post: Post, output_dir: Path) -> Path:
    date_prefix = post.created_at.strftime("%Y-%m-%d")
    slug = _slugify(post.title)
    filename = f"{date_prefix}_{slug}.md"
    platform_dir = output_dir / "posts" / post.platform
    platform_dir.mkdir(parents=True, exist_ok=True)

    filepath = platform_dir / filename

    content = "\n\n".join((_frontmatter(post), post.body))
    filepath.write_text(content, encoding="utf-8")
    return filepath
