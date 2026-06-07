from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import click

from app.cli.config import build_settings_from_cli
from app.core.quality_gate import QualityGate
from app.db.engine import create_db_engine, create_session_factory
from app.db.repository import save_event_clusters, save_ingestion_result
from app.posting.publishers import TelegramPublisher
from app.services.events.engine import EventEngine
from app.services.factory import build_content_services
from app.services.ingestion.service import IngestionService
from app.workflows.persistent_workflow import PersistentWorkflowRunner


@click.command()
@click.option("--lookback-hours", type=int, default=24, help="How far back to pull source documents.")
@click.option("--limit", type=int, default=3, help="How many top event clusters to process.")
@click.option("--data-dir", type=click.Path(), default=None, help="Output directory for generated posts.")
@click.option("--database-url", default=None, help="Database connection URL.")
@click.option("--telegram-bot-token", default=None, help="Telegram bot token for publishing.")
@click.option("--telegram-chat-id", default=None, help="Telegram chat ID for publishing.")
@click.pass_context
def pipeline(
    ctx: click.Context,
    lookback_hours: int,
    limit: int,
    data_dir: str | None,
    database_url: str | None,
    telegram_bot_token: str | None,
    telegram_chat_id: str | None,
) -> None:
    """Run the full content pipeline: ingest -> cluster -> research -> draft -> QA -> publish."""
    output_json: bool = ctx.obj["output_json"]
    env_file: str | None = ctx.obj.get("env_file")
    settings = build_settings_from_cli(
        env_file=env_file,
        data_dir=data_dir,
        database_url=database_url,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
    )

    now = datetime.now(timezone.utc)

    engine = create_db_engine(settings.database_url, echo=settings.database_echo)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        ingestion_service = IngestionService(settings=settings)
        ingest_result = ingestion_service.ingest_recent_documents_with_errors(
            now=now, lookback_hours=lookback_hours
        )

        ingest_run_id = str(uuid4())
        save_ingestion_result(session, ingest_result, ingest_run_id, lookback_hours)
        session.flush()

        clusters = EventEngine().select_top_clusters(
            documents=ingest_result.documents, now=now, limit=limit
        )
        save_event_clusters(session, clusters, {})
        session.flush()

        content_services = build_content_services(settings=settings)
        tg = (
            TelegramPublisher(bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id)
            if settings.telegram_bot_token and settings.telegram_chat_id
            else None
        )
        runner = PersistentWorkflowRunner(
            session=session,
            content_services=content_services,
            quality_gate=QualityGate(),
            output_dir=settings.data_dir,
            publishers=[tg] if tg else [],
        )

        results = []
        for cluster in clusters:
            result = runner.run_for_cluster(cluster, topic=cluster.headline)
            results.append(result)

        job_ids = [r.job.job_id for r in results]
        final_statuses = [r.job.status for r in results]

        if output_json:
            click.echo(
                json.dumps(
                    {
                        "environment": settings.environment,
                        "document_count": len(ingest_result.documents),
                        "cluster_count": len(clusters),
                        "error_count": len(ingest_result.source_errors),
                        "job_ids": job_ids,
                        "final_statuses": final_statuses,
                        "data_dir": str(settings.data_dir),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            click.echo(f"environment: {settings.environment}")
            click.echo(f"document_count: {len(ingest_result.documents)}")
            click.echo(f"cluster_count: {len(clusters)}")
            click.echo(f"error_count: {len(ingest_result.source_errors)}")
            click.echo(f"job_ids: {', '.join(job_ids) if job_ids else 'none'}")
            click.echo(f"final_statuses: {', '.join(final_statuses) if final_statuses else 'none'}")
            if settings.data_dir:
                click.echo(f"posts written to: {settings.data_dir}/posts/")

    engine.dispose()
