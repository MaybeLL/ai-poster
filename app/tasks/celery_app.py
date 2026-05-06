from __future__ import annotations

from celery import Celery

from app.core.settings import AppSettings

settings = AppSettings.from_env()

celery_app = Celery(
    "ai_poster",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "daily-pipeline-run": {
            "task": "app.tasks.pipeline_tasks.run_full_pipeline_task",
            "schedule": 86400.0,  # every 24 hours
            "args": (24, 3),
        },
    },
)
