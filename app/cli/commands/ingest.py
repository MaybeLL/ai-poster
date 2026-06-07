from __future__ import annotations

import json
from datetime import datetime, timezone

import click

from app.cli.config import build_settings_from_cli
from app.main import build_ingestion_summary


@click.command()
@click.option("--lookback-hours", type=int, default=24, help="How far back to pull source documents.")
@click.pass_context
def ingest(ctx: click.Context, lookback_hours: int) -> None:
    """Fetch recent documents from configured RSS sources."""
    output_json: bool = ctx.obj["output_json"]
    env_file: str | None = ctx.obj.get("env_file")
    settings = build_settings_from_cli(env_file=env_file)
    now = datetime.now(timezone.utc)
    result = build_ingestion_summary(settings=settings, now=now, lookback_hours=lookback_hours)
    if output_json:
        lines = result.strip().split("\n")
        data = {}
        for line in lines:
            if ": " in line:
                key, _, val = line.partition(": ")
                data[key.strip()] = val.strip()
        data["document_count"] = int(data.get("document_count", "0"))
        data["source_count"] = int(data.get("source_count", "0"))
        data["error_count"] = int(data.get("error_count", "0"))
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(result)
