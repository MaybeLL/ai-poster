from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.posting.models import Post

logger = logging.getLogger(__name__)

TG_MSG_MAX = 4000


class Publisher(Protocol):
    def publish(self, post: Post) -> str | None:
        """Publish a post. Returns a URL or None."""
        ...


class TelegramPublisher:
    """Publishes posts to a Telegram chat via bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.chat_id = chat_id

    def publish(self, post: Post) -> str | None:
        if not self.chat_id or "bot" not in self.api_url:
            logger.debug("Telegram not configured, skipping")
            return None

        platform_icon = {"wechat": "📰", "xiaohongshu": "📕"}.get(post.platform, "📌")
        tags_line = "  ".join(post.tags) if post.tags else ""

        lines = [f"{platform_icon}  <b>{post.title}</b>", "", post.body]
        if tags_line:
            lines.extend(["", tags_line])
        text = "\n".join(lines)

        if len(text) > TG_MSG_MAX:
            text = text[: TG_MSG_MAX - 100].rsplit("\n", 1)[0] + "\n\n..."

        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}

        try:
            resp = httpx.post(self.api_url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("ok"):
                logger.info("Telegram push succeeded for %s post", post.platform)
                return f"tg://{post.platform}"
            logger.warning("Telegram push returned error: %s", data)
        except Exception as exc:
            logger.warning("Telegram push failed: %s", exc)

        return None
