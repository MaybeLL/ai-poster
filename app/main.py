from __future__ import annotations

import argparse
from datetime import datetime, timezone
from shutil import which
from typing import Callable

from app.agents.provider import AgentInvocation, ProviderExecutionResult
from app.agents.smoke import run_agent_smoke
from app.core.quality_gate import QualityGateInput
from app.core.quality_gate import QualityGate
from app.core.settings import AppSettings
from app.posting.publishers import TelegramPublisher
from app.posting.writer import write_post
from app.services.events.engine import EventEngine
from app.services.factory import build_content_services
from app.services.ingestion.service import IngestionService
from app.services.research.service import ResearchService
from app.workflows.mvp_workflow import MvpWorkflowRunner


def build_demo_summary(topic: str) -> str:
    runner = MvpWorkflowRunner()
    result = runner.run(
        topic=topic,
        qa_input=QualityGateInput(
            total_score=84,
            factual_accuracy_score=95,
            viewpoint_clarity_score=80,
            sources_verified=True,
            within_time_window=True,
            claims_supported=True,
            long_short_consistent=True,
        ),
    )
    failed_checks = ", ".join(result.decision.failed_checks) if result.decision.failed_checks else "none"
    completed_stages = " -> ".join(result.completed_stages)
    return "\n".join(
        (
            f"topic: {topic}",
            f"final_status: {result.job.status}",
            f"failed_checks: {failed_checks}",
            f"stages: {completed_stages}",
        )
    )


def build_ingestion_summary(
    settings: AppSettings,
    now: datetime,
    lookback_hours: int,
    fetcher: Callable[[str], str] | None = None,
) -> str:
    service = IngestionService(settings=settings, fetcher=fetcher)
    result = service.ingest_recent_documents_with_errors(now=now, lookback_hours=lookback_hours)
    documents = result.documents
    source_count = len({document.source_id for document in documents})
    titles = ", ".join(document.title for document in documents[:5]) if documents else "none"
    return "\n".join(
        (
            f"environment: {settings.environment}",
            f"source_count: {source_count}",
            f"document_count: {len(documents)}",
            f"error_count: {len(result.source_errors)}",
            f"sample_titles: {titles}",
        )
    )


def build_event_summary(
    settings: AppSettings,
    now: datetime,
    lookback_hours: int,
    limit: int,
    fetcher: Callable[[str], str] | None = None,
) -> str:
    ingestion_service = IngestionService(settings=settings, fetcher=fetcher)
    result = ingestion_service.ingest_recent_documents_with_errors(now=now, lookback_hours=lookback_hours)
    documents = result.documents
    clusters = EventEngine().select_top_clusters(documents=documents, now=now, limit=limit)
    top_headlines = ", ".join(cluster.headline for cluster in clusters) if clusters else "none"
    return "\n".join(
        (
            f"environment: {settings.environment}",
            f"document_count: {len(documents)}",
            f"cluster_count: {len(clusters)}",
            f"error_count: {len(result.source_errors)}",
            f"top_headlines: {top_headlines}",
        )
    )


def build_research_summary(
    settings: AppSettings,
    now: datetime,
    lookback_hours: int,
    limit: int,
    fetcher: Callable[[str], str] | None = None,
) -> str:
    ingestion_service = IngestionService(settings=settings, fetcher=fetcher)
    result = ingestion_service.ingest_recent_documents_with_errors(now=now, lookback_hours=lookback_hours)
    documents = result.documents
    clusters = EventEngine().select_top_clusters(documents=documents, now=now, limit=limit)
    packets = [ResearchService().build_packet(cluster) for cluster in clusters]
    top_lines = ", ".join(
        f"{packet.headline} (source_brief_count: {len(packet.source_briefs)})" for packet in packets
    ) if packets else "none"
    return "\n".join(
        (
            f"environment: {settings.environment}",
            f"packet_count: {len(packets)}",
            f"error_count: {len(result.source_errors)}",
            f"top_packets: {top_lines}",
        )
    )


def build_pipeline_summary(
    settings: AppSettings,
    now: datetime,
    lookback_hours: int,
    limit: int,
    fetcher: Callable[[str], str] | None = None,
) -> str:
    ingestion_service = IngestionService(settings=settings, fetcher=fetcher)
    result = ingestion_service.ingest_recent_documents_with_errors(now=now, lookback_hours=lookback_hours)
    documents = result.documents
    clusters = EventEngine().select_top_clusters(documents=documents, now=now, limit=limit)
    content_services = build_content_services(settings=settings)
    packets = [content_services.research_service.build_packet(cluster) for cluster in clusters]
    gate = QualityGate()
    draft_packages = [content_services.writing_service.build_draft_package(packet) for packet in packets]
    review_results = [
        content_services.qa_service.review_package(packet, draft_package)
        for packet, draft_package in zip(packets, draft_packages)
    ]
    decisions = [gate.evaluate(review.to_quality_gate_input()) for review in review_results]
    final_status = "accepted" if decisions and all(decision.accepted for decision in decisions) else "rejected"

    tg = (
        TelegramPublisher(bot_token=settings.telegram_bot_token, chat_id=settings.telegram_chat_id)
        if settings.telegram_bot_token and settings.telegram_chat_id
        else None
    )

    for packet, draft_package, cluster in zip(packets, draft_packages, clusters):
        posts = content_services.posting_service.generate_posts(packet, draft_package, job_id=cluster.cluster_id)
        for post in posts:
            path = write_post(post, settings.data_dir)
            _ = path
            if tg:
                tg.publish(post)

    top_headlines = ", ".join(packet.headline for packet in packets) if packets else "none"
    return "\n".join(
        (
            f"environment: {settings.environment}",
            f"packet_count: {len(packets)}",
            f"error_count: {len(result.source_errors)}",
            f"final_status: {final_status}",
            f"top_headlines: {top_headlines}",
        )
    )


def build_agent_probe_summary(
    settings: AppSettings,
    resolver: Callable[[str], str | None] = which,
) -> str:
    if settings.intelligence_backend == "rule":
        return "\n".join(
            (
                f"environment: {settings.environment}",
                "backend: rule",
                "resolved_executable: none",
            )
        )

    command = (
        settings.codex_command
        if settings.intelligence_backend == "codex"
        else settings.claude_code_command
    )
    executable = command[0]
    resolved = resolver(executable)
    return "\n".join(
        (
            f"environment: {settings.environment}",
            f"backend: {settings.intelligence_backend}",
            f"configured_command: {' '.join(command)}",
            f"configured_env_keys: {', '.join(sorted((settings.codex_env if settings.intelligence_backend == 'codex' else settings.claude_code_env).keys())) or 'none'}",
            f"resolved_executable: {resolved or 'missing'}",
        )
    )


def build_agent_smoke_summary(
    settings: AppSettings,
    executor: Callable[[AgentInvocation], ProviderExecutionResult] | None = None,
) -> str:
    result = run_agent_smoke(settings=settings, executor=executor)
    payload_status = result.payload.get("status", "none") if result.payload else "none"
    return "\n".join(
        (
            f"environment: {settings.environment}",
            f"backend: {result.backend}",
            f"smoke_status: {result.status}",
            f"payload_status: {payload_status}",
            f"error: {result.error_message or 'none'}",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI Poster MVP demo workflow.")
    parser.add_argument(
        "--mode",
        choices=("demo-workflow", "ingest", "rank-events", "research", "pipeline", "agent-probe", "agent-smoke"),
        default="demo-workflow",
        help="Execution mode for the local MVP CLI.",
    )
    parser.add_argument(
        "--topic",
        default="OpenAI releases a new multimodal agent capability",
        help="Topic to run through the local MVP workflow demo.",
    )
    parser.add_argument(
        "--lookback-hours",
        type=int,
        default=24,
        help="How far back to pull source documents in ingestion mode.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="How many top event clusters to return in rank-events mode.",
    )
    args = parser.parse_args()
    if args.mode == "demo-workflow":
        print(build_demo_summary(args.topic))
        return

    settings = AppSettings.from_env()
    now = datetime.now(timezone.utc)
    if args.mode == "ingest":
        print(
            build_ingestion_summary(
                settings=settings,
                now=now,
                lookback_hours=args.lookback_hours,
            )
        )
        return

    if args.mode == "rank-events":
        print(
            build_event_summary(
                settings=settings,
                now=now,
                lookback_hours=args.lookback_hours,
                limit=args.limit,
            )
        )
        return

    if args.mode == "research":
        print(
            build_research_summary(
                settings=settings,
                now=now,
                lookback_hours=args.lookback_hours,
                limit=args.limit,
            )
        )
        return

    if args.mode == "agent-probe":
        print(build_agent_probe_summary(settings=settings))
        return

    if args.mode == "agent-smoke":
        print(build_agent_smoke_summary(settings=settings))
        return

    print(
        build_pipeline_summary(
            settings=settings,
            now=now,
            lookback_hours=args.lookback_hours,
            limit=args.limit,
        )
    )


if __name__ == "__main__":
    main()
