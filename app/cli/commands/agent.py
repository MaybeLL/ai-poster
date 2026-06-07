from __future__ import annotations

import json

import click

from app.cli.config import build_settings_from_cli
from app.main import build_agent_probe_summary, build_agent_smoke_summary


@click.group()
def agent() -> None:
    """Probe or smoke-test the configured intelligence backend."""


@agent.command()
@click.pass_context
def probe(ctx: click.Context) -> None:
    """Check whether the configured agent backend is reachable."""
    output_json: bool = ctx.obj["output_json"]
    env_file: str | None = ctx.obj.get("env_file")
    settings = build_settings_from_cli(env_file=env_file)
    result = build_agent_probe_summary(settings=settings)
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


@agent.command()
@click.pass_context
def smoke(ctx: click.Context) -> None:
    """Run a smoke test (full invocation) against the configured backend."""
    output_json: bool = ctx.obj["output_json"]
    env_file: str | None = ctx.obj.get("env_file")
    settings = build_settings_from_cli(env_file=env_file)
    result = build_agent_smoke_summary(settings=settings)
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
