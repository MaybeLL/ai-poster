from __future__ import annotations

from pathlib import Path

import click


def _get_alembic_config():
    import app as app_pkg

    from alembic.config import Config

    project_root = Path(app_pkg.__file__).parent.parent
    ini_path = project_root / "alembic.ini"
    if not ini_path.exists():
        raise click.ClickException(f"alembic.ini not found at {ini_path}")
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(project_root / "alembic"))
    return cfg


@click.group()
def migrate() -> None:
    """Manage database migrations (alembic wrapper)."""


@migrate.command()
@click.option("--revision", default="head", help="Target revision (default: head).")
def upgrade(revision: str) -> None:
    """Upgrade database to the specified revision."""
    from alembic import command

    cfg = _get_alembic_config()
    command.upgrade(cfg, revision)
    click.echo(f"Database upgraded to: {revision}")


@migrate.command()
@click.option("--revision", default="-1", help="Target revision (default: -1, one step down).")
def downgrade(revision: str) -> None:
    """Downgrade database to the specified revision."""
    from alembic import command

    cfg = _get_alembic_config()
    command.downgrade(cfg, revision)
    click.echo(f"Database downgraded to: {revision}")


@migrate.command()
def current() -> None:
    """Show the current database revision."""
    from alembic import command

    cfg = _get_alembic_config()
    command.current(cfg)


@migrate.command()
def history() -> None:
    """Show migration history."""
    from alembic import command

    cfg = _get_alembic_config()
    command.history(cfg)
