from __future__ import annotations

import json
from datetime import datetime, timezone

import click

from app.cli.config import build_settings_from_cli
from app.main import build_research_summary


@click.command()
@click.option("--lookback-hours", type=int, default=24, help="How far back to pull source documents.")
@click.option("--limit", type=int, default=3, help="How many research packets to produce.")
@click.pass_context
def research(ctx: click.Context, lookback_hours: int, limit: int) -> None:
    """Build research packets for top event clusters."""
    output_json: bool = ctx.obj["output_json"]
    env_file: str | None = ctx.obj.get("env_file")
    settings = build_settings_from_cli(env_file=env_file)
    now = datetime.now(timezone.utc)
    result = build_research_summary(settings=settings, now=now, lookback_hours=lookback_hours, limit=limit)
    if output_json:
        lines = result.strip().split("\n")
        data = {}
        for line in lines:
            if ": " in line:
                key, _, val = line.partition(": ")
                data[key.strip()] = val.strip()
        data["packet_count"] = int(data.get("packet_count", "0"))
        data["error_count"] = int(data.get("error_count", "0"))
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(result)
