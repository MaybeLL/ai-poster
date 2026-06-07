from __future__ import annotations

import json
import sys
from typing import Any

import click

from app.cli.commands.agent import agent
from app.cli.commands.demo import demo
from app.cli.commands.events import events
from app.cli.commands.ingest import ingest
from app.cli.commands.migrate import migrate
from app.cli.commands.pipeline import pipeline
from app.cli.commands.research import research
from app.cli.commands.serve import serve
from app.cli.config import build_settings_from_cli


def _format_output(result: dict[str, Any] | str, output_json: bool) -> str:
    if output_json:
        if isinstance(result, str):
            lines = result.strip().split("\n")
            data: dict[str, Any] = {}
            for line in lines:
                if ": " in line:
                    key, _, val = line.partition(": ")
                    data[key.strip()] = val.strip()
            result = data
        return json.dumps(result, ensure_ascii=False, default=str, indent=2)
    return result if isinstance(result, str) else str(result)


@click.group()
@click.option("--json", "output_json", is_flag=True, default=False, help="Output in JSON format.")
@click.option("--env-file", type=click.Path(exists=True), default=None, help="Path to .env file.")
@click.version_option(version="0.1.0", prog_name="ai-poster")
@click.pass_context
def main(ctx: click.Context, output_json: bool, env_file: str | None) -> None:
    """AI Poster — automated content production for AI industry news.

    Fetch RSS feeds, cluster events, research topics, draft articles,
    run quality checks, and publish to content platforms.
    """
    ctx.ensure_object(dict)
    ctx.obj["output_json"] = output_json
    ctx.obj["env_file"] = env_file
    ctx.obj["settings"] = build_settings_from_cli(env_file=env_file)


main.add_command(demo)
main.add_command(ingest)
main.add_command(events)
main.add_command(research)
main.add_command(pipeline)
main.add_command(serve)
main.add_command(migrate)
main.add_command(agent)


if __name__ == "__main__":
    main()
