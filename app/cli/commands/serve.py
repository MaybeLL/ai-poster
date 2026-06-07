from __future__ import annotations

import click


@click.command()
@click.option("--host", default=None, help="Host to bind the API server.")
@click.option("--port", type=int, default=None, help="Port to bind the API server.")
@click.option("--reload/--no-reload", default=False, help="Enable auto-reload for development.")
@click.pass_context
def serve(ctx: click.Context, host: str | None, port: int | None, reload: bool) -> None:
    """Start the FastAPI web server."""
    import uvicorn

    settings = ctx.obj.get("settings")
    host = host or (settings.api_host if settings else "127.0.0.1")
    port = port or (settings.api_port if settings else 8000)
    click.echo(f"Starting AI Poster API on http://{host}:{port}")
    uvicorn.run("app.web.app:app", host=host, port=port, reload=reload)
