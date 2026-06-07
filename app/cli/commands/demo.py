from __future__ import annotations

import json

import click

from app.main import build_demo_summary


@click.command()
@click.option("--topic", default="OpenAI releases a new multimodal agent capability", help="Topic for the demo workflow.")
@click.pass_context
def demo(ctx: click.Context, topic: str) -> None:
    """Run a quick demo of the full pipeline with mock QA scores."""
    output_json: bool = ctx.obj["output_json"]
    result = build_demo_summary(topic)
    if output_json:
        lines = result.strip().split("\n")
        data = {}
        for line in lines:
            if ": " in line:
                key, _, val = line.partition(": ")
                data[key.strip()] = val.strip()
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        click.echo(result)
