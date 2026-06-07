from __future__ import annotations

import json
from datetime import datetime, timezone

import click

from app.cli.config import build_settings_from_cli
from app.main import build_event_summary


@click.command()
@click.option("--lookback-hours", type=int, default=24, help="How far back to pull source documents.")
@click.option("--limit", type=int, default=3, help="How many top event clusters to return.")
@click.pass_context
def events(ctx: click.Context, lookback_hours: int, limit: int) -> None:
    """Rank top event clusters from recent documents."""
    output_json: bool = ctx.obj["output_json"]
    env_file: str | None = ctx.obj.get("env_file")
    settings = build_settings_from_cli(env_file=env_file)
    now = datetime.now(timezone.utc)
    result = build_event_summary(settings=settings, now=now, lookback_hours=lookback_hours, limit=limit)
    if output_json:
        lines = result.strip().split("\n")
        data = {}
        for line in lines:
            if ": " in line:
                key, _, val = line.partition(": ")
                data[key.strip()] = val.strip()
        data["document_count"] = int(data.get("document_count", "0"))
        data["cluster_count"] = int(data.get("cluster_count", "0"))
        data["error_count"] = int(data.get("error_count", "0"))
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(result)
