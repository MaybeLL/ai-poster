import unittest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.quality_gate import QualityGate
from app.db.models import Base
from app.db.repository import get_job_by_id, get_research_packet, get_draft_package
from app.services.events.engine import EventCluster, EventScore
from app.services.factory import build_content_services
from app.services.ingestion.rss_adapter import RawDocument
from app.workflows.persistent_workflow import PersistentWorkflowRunner


class PersistentWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)

    def _make_cluster(self) -> EventCluster:
        return EventCluster(
            cluster_id="c1",
            headline="OpenAI releases GPT-5",
            documents=[
                RawDocument(
                    source_id="openai-blog",
                    title="OpenAI releases GPT-5",
                    url="https://openai.com/gpt-5",
                    summary="GPT-5 announced with new features.",
                    published_at=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
                    authority_weight=10,
                )
            ],
            score=EventScore(
                freshness_score=28.0,
                authority_score=50.0,
                coverage_score=4.0,
                total_score=82.0,
            ),
        )

    def test_run_for_cluster_persists_everything(self) -> None:
        from app.core.settings import AppSettings

        settings = AppSettings(
            environment="test",
            data_dir=__import__("pathlib").Path("data"),
        )
        services = build_content_services(settings=settings)
        runner = PersistentWorkflowRunner(
            session=self.session,
            content_services=services,
            quality_gate=QualityGate(),
        )

        cluster = self._make_cluster()
        result = runner.run_for_cluster(cluster, topic="OpenAI releases GPT-5")

        self.assertIsNotNone(result.job.job_id)
        self.assertIn(result.job.status, ("accepted", "rejected"))

        retrieved_job = get_job_by_id(self.session, result.job.job_id)
        self.assertIsNotNone(retrieved_job)

        packet = get_research_packet(self.session, result.job.job_id)
        self.assertIsNotNone(packet)
        self.assertEqual(packet.cluster_id, cluster.cluster_id)

        draft = get_draft_package(self.session, result.job.job_id)
        self.assertIsNotNone(draft)

    def test_run_for_cluster_rolls_back_on_failure(self) -> None:
        from app.core.settings import AppSettings

        settings = AppSettings(
            environment="test",
            data_dir=__import__("pathlib").Path("data"),
        )
        services = build_content_services(settings=settings)
        runner = PersistentWorkflowRunner(
            session=self.session,
            content_services=services,
            quality_gate=QualityGate(),
        )

        cluster = self._make_cluster()
        result = runner.run_for_cluster(cluster, topic="Test")

        self.assertIn(result.job.status, ("accepted", "rejected"))


if __name__ == "__main__":
    unittest.main()
