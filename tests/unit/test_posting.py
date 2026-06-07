import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.provider import AgentInvocation, AgentRequest, ProviderExecutionResult
from app.core.settings import AppSettings
from app.db.adapters import model_to_post, post_to_model
from app.db.models import Base, PostModel
from app.db.repository import get_post_by_id, get_posts_by_job_id, save_posts
from app.posting.models import Post
from app.posting.pipelines.wechat import WeChatPostPipeline
from app.posting.pipelines.xiaohongshu import XiaohongshuPostPipeline
from app.posting.service import PostingService
from app.services.factory import build_content_services
from app.services.ingestion.rss_adapter import RawDocument
from app.services.events.engine import EventCluster, EventScore
from app.services.research.service import ResearchPacket, SourceBrief, TimelineEntry
from app.services.writing.service import DraftArticle, DraftPackage


def _make_packet() -> ResearchPacket:
    return ResearchPacket(
        cluster_id="cluster-test-1",
        headline="OpenAI releases GPT-5 with improved reasoning",
        event_summary="OpenAI announced GPT-5, a major upgrade with enhanced reasoning capabilities.",
        primary_source_summary="GPT-5 brings chain-of-thought improvements and native multimodal support.",
        source_briefs=[
            SourceBrief(
                source_id="openai-blog",
                title="OpenAI releases GPT-5",
                url="https://openai.com/gpt-5",
                summary="GPT-5 announced.",
                published_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
                authority_weight=10,
            )
        ],
        timeline=[
            TimelineEntry(
                source_id="openai-blog",
                title="OpenAI releases GPT-5",
                published_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
            )
        ],
        keywords=["GPT-5", "reasoning", "multimodal", "OpenAI"],
        open_questions=["API pricing?"],
    )


def _make_draft() -> DraftPackage:
    return DraftPackage(
        long_article=DraftArticle(
            cluster_id="cluster-test-1",
            title="GPT-5 发布：推理能力实现质的飞跃",
            body="## 事件概述\n\nOpenAI 发布了 GPT-5，推理能力大幅提升。\n\n## 核心看点\n\nGPT-5 带来了多项突破。\n\n## 关键判断\n\n这是重大进步。",
        ),
        short_post=DraftArticle(
            cluster_id="cluster-test-1",
            title="GPT-5 来了！",
            body="📌 GPT-5 发布了！\n\nOpenAI 刚刚发布了 GPT-5...\n\n💡 推理能力大幅提升",
        ),
    )


class PostModelTest(unittest.TestCase):
    def test_to_dict_roundtrip(self) -> None:
        now = datetime.now(timezone.utc)
        post = Post(
            post_id="p1",
            job_id="j1",
            platform="wechat",
            title="Title",
            body="Body text",
            tags=["AI", "GPT"],
            status="draft",
            published_at=now,
            url="https://example.com",
            created_at=now,
        )
        d = post.to_dict()
        restored = Post.from_dict(d)
        self.assertEqual(restored.post_id, "p1")
        self.assertEqual(restored.platform, "wechat")
        self.assertEqual(restored.tags, ["AI", "GPT"])
        self.assertEqual(restored.url, "https://example.com")

    def test_default_status_is_draft(self) -> None:
        post = Post(post_id="p1", job_id="j1", platform="wechat", title="T", body="B")
        self.assertEqual(post.status, "draft")


class WeChatPipelineTest(unittest.TestCase):
    def test_rule_fallback_uses_draft_content(self) -> None:
        pipeline = WeChatPostPipeline()
        packet = _make_packet()
        draft = _make_draft()
        post = pipeline.build_post(packet, draft, job_id="j1")

        self.assertEqual(post.platform, "wechat")
        self.assertIn("GPT-5", post.title)
        self.assertIn("事件概述", post.body)
        self.assertGreater(len(post.body), 50)

    def test_agent_mode_uses_provider(self) -> None:
        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            return ProviderExecutionResult(
                stdout=json.dumps({
                    "type": "result",
                    "structured_output": {
                        "title": "GPT-5 发布：推理能力质的飞跃",
                        "body": "## 事件概述\n\nOpenAI 发布了 GPT-5。",
                        "tags": ["GPT-5", "AI"],
                    },
                }),
                stderr="",
                returncode=0,
            )

        settings = AppSettings(
            environment="test",
            data_dir=__import__("pathlib").Path("data"),
            intelligence_backend="claude-code",
        )
        from app.agents.factory import build_agent_provider
        provider = build_agent_provider(settings=settings, executor=executor)
        pipeline = WeChatPostPipeline(provider=provider)
        packet = _make_packet()
        draft = _make_draft()
        post = pipeline.build_post(packet, draft, job_id="j1")

        self.assertEqual(post.platform, "wechat")
        self.assertIn("GPT-5", post.title)
        self.assertEqual(post.tags, ["GPT-5", "AI"])

    def test_agent_failure_falls_back_to_draft(self) -> None:
        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            raise RuntimeError("agent crashed")

        settings = AppSettings(
            environment="test",
            data_dir=__import__("pathlib").Path("data"),
            intelligence_backend="claude-code",
        )
        from app.agents.factory import build_agent_provider
        provider = build_agent_provider(settings=settings, executor=executor)
        pipeline = WeChatPostPipeline(provider=provider)
        packet = _make_packet()
        draft = _make_draft()
        post = pipeline.build_post(packet, draft, job_id="j1")

        self.assertEqual(post.platform, "wechat")
        self.assertIn("GPT-5", post.title)  # falls back to draft title


class XiaohongshuPipelineTest(unittest.TestCase):
    def test_rule_fallback_uses_draft_content(self) -> None:
        pipeline = XiaohongshuPostPipeline()
        packet = _make_packet()
        draft = _make_draft()
        post = pipeline.build_post(packet, draft, job_id="j1")

        self.assertEqual(post.platform, "xiaohongshu")
        self.assertIn("GPT-5", post.title)
        self.assertIn("📌", post.body)

    def test_agent_mode_uses_provider(self) -> None:
        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            return ProviderExecutionResult(
                stdout=json.dumps({
                    "type": "result",
                    "structured_output": {
                        "title": "GPT-5 来了！",
                        "body": "OpenAI 刚刚发布了 GPT-5...",
                        "tags": ["#AI", "#GPT5"],
                    },
                }),
                stderr="",
                returncode=0,
            )

        settings = AppSettings(
            environment="test",
            data_dir=__import__("pathlib").Path("data"),
            intelligence_backend="claude-code",
        )
        from app.agents.factory import build_agent_provider
        provider = build_agent_provider(settings=settings, executor=executor)
        pipeline = XiaohongshuPostPipeline(provider=provider)
        packet = _make_packet()
        draft = _make_draft()
        post = pipeline.build_post(packet, draft, job_id="j1")

        self.assertEqual(post.platform, "xiaohongshu")
        self.assertIn("GPT-5", post.title)
        self.assertEqual(post.tags, ["#AI", "#GPT5"])

    def test_agent_failure_falls_back_to_draft(self) -> None:
        def executor(invocation: AgentInvocation) -> ProviderExecutionResult:
            raise RuntimeError("agent crashed")

        settings = AppSettings(
            environment="test",
            data_dir=__import__("pathlib").Path("data"),
            intelligence_backend="claude-code",
        )
        from app.agents.factory import build_agent_provider
        provider = build_agent_provider(settings=settings, executor=executor)
        pipeline = XiaohongshuPostPipeline(provider=provider)
        packet = _make_packet()
        draft = _make_draft()
        post = pipeline.build_post(packet, draft, job_id="j1")

        self.assertEqual(post.platform, "xiaohongshu")
        self.assertIn("📌", post.body)  # falls back to draft content


class PostingServiceTest(unittest.TestCase):
    def test_generate_posts_runs_all_pipelines(self) -> None:
        service = PostingService(pipelines={
            "wechat": WeChatPostPipeline(),
            "xiaohongshu": XiaohongshuPostPipeline(),
        })
        packet = _make_packet()
        draft = _make_draft()
        posts = service.generate_posts(packet, draft, job_id="j1")

        self.assertEqual(len(posts), 2)
        platforms = {p.platform for p in posts}
        self.assertEqual(platforms, {"wechat", "xiaohongshu"})

    def test_platforms_property(self) -> None:
        service = PostingService(pipelines={
            "w": WeChatPostPipeline(),
            "x": XiaohongshuPostPipeline(),
        })
        self.assertCountEqual(service.platforms, ["w", "x"])

    def test_empty_pipelines(self) -> None:
        service = PostingService(pipelines={})
        packet = _make_packet()
        draft = _make_draft()
        posts = service.generate_posts(packet, draft, job_id="j1")
        self.assertEqual(posts, [])


class PostRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.job_id = str(uuid4())

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def test_save_and_retrieve_posts(self) -> None:
        posts = [
            Post(post_id="p1", job_id=self.job_id, platform="wechat", title="W Title", body="W Body", tags=["AI"]),
            Post(post_id="p2", job_id=self.job_id, platform="xiaohongshu", title="X Title", body="X Body", tags=["#AI"]),
        ]
        save_posts(self.session, posts, self.job_id)

        retrieved = get_posts_by_job_id(self.session, self.job_id)
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0].platform, "wechat")
        self.assertEqual(retrieved[1].platform, "xiaohongshu")

    def test_get_post_by_id(self) -> None:
        post = Post(post_id="p1", job_id=self.job_id, platform="wechat", title="T", body="B")
        save_posts(self.session, [post], self.job_id)

        retrieved = get_post_by_id(self.session, "p1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "T")

    def test_get_post_by_id_not_found(self) -> None:
        retrieved = get_post_by_id(self.session, "nonexistent")
        self.assertIsNone(retrieved)

    def test_get_posts_by_job_id_empty(self) -> None:
        retrieved = get_posts_by_job_id(self.session, "nonexistent")
        self.assertEqual(retrieved, [])


class PostAdapterTest(unittest.TestCase):
    def test_post_to_model_and_back(self) -> None:
        now = datetime.now(timezone.utc)
        post = Post(
            post_id="p1",
            job_id="j1",
            platform="xiaohongshu",
            title="T",
            body="B",
            tags=["#AI", "#GPT"],
            status="draft",
            created_at=now,
        )
        model = post_to_model(post, job_id="j1")
        self.assertEqual(model.post_id, "p1")
        self.assertEqual(model.tags_json, json.dumps(["#AI", "#GPT"]))

        restored = model_to_post(model)
        self.assertEqual(restored.post_id, "p1")
        self.assertEqual(restored.tags, ["#AI", "#GPT"])
        self.assertEqual(restored.created_at.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"))


class PostWriterTest(unittest.TestCase):
    def test_write_post_creates_md_file(self) -> None:
        from app.posting.writer import write_post

        post = Post(
            post_id="pw1",
            job_id="j1",
            platform="wechat",
            title="GPT-5 深度解读",
            body="## 事件概述\n\nGPT-5 发布了。",
            tags=["GPT-5", "AI"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = write_post(post, Path(tmp))
            self.assertTrue(path.exists())
            self.assertIn("wechat", str(path))
            self.assertIn(".md", path.suffix)

            content = path.read_text(encoding="utf-8")
            self.assertIn("platform:", content)
            self.assertIn("GPT-5 深度解读", content)
            self.assertIn("GPT-5 发布了", content)
            self.assertIn("---", content)

    def test_write_post_handles_mixed_chars_in_title(self) -> None:
        from app.posting.writer import write_post

        post = Post(
            post_id="pw2",
            job_id="j1",
            platform="xiaohongshu",
            title="GPT-5 来了！🔥",
            body="内容正文",
            tags=["#AI"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = write_post(post, Path(tmp))
            self.assertTrue(path.exists())
            self.assertIn("xiaohongshu", str(path))


class TelegramPublisherTest(unittest.TestCase):
    def test_publish_skipped_when_not_configured(self) -> None:
        from app.posting.publishers import TelegramPublisher

        publisher = TelegramPublisher(bot_token="", chat_id="")
        post = Post(post_id="p", job_id="j", platform="wechat", title="T", body="B")
        result = publisher.publish(post)
        self.assertIsNone(result)

    def test_publish_sends_message(self) -> None:
        from unittest.mock import patch

        from app.posting.publishers import TelegramPublisher

        publisher = TelegramPublisher(bot_token="123:abc", chat_id="-100")
        post = Post(
            post_id="p1",
            job_id="j1",
            platform="xiaohongshu",
            title="Test Post",
            body="Hello world",
            tags=["#AI"],
        )

        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"ok": True}

            result = publisher.publish(post)
            self.assertEqual(result, "tg://xiaohongshu")

            _, kwargs = mock_post.call_args
            self.assertEqual(kwargs["json"]["chat_id"], "-100")
            self.assertIn("Test Post", kwargs["json"]["text"])
            self.assertEqual(kwargs["json"]["parse_mode"], "HTML")

    def test_publish_truncates_long_body(self) -> None:
        from unittest.mock import patch

        from app.posting.publishers import TG_MSG_MAX, TelegramPublisher

        publisher = TelegramPublisher(bot_token="123:abc", chat_id="-100")
        long_body = "line\n" * (TG_MSG_MAX // 5)
        post = Post(post_id="p2", job_id="j1", platform="wechat", title="Long", body=long_body)

        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"ok": True}

            publisher.publish(post)
            sent_text = mock_post.call_args[1]["json"]["text"]
            self.assertLessEqual(len(sent_text), TG_MSG_MAX + 100)


if __name__ == "__main__":
    unittest.main()
