from __future__ import annotations

from fastapi import FastAPI

from app.core.settings import AppSettings
from app.db.engine import create_db_engine, create_session_factory
from app.web.state import init_state


def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or AppSettings.from_env()
    engine = create_db_engine(settings.database_url, echo=settings.database_echo)
    session_factory = create_session_factory(engine)

    init_state(settings, engine, session_factory)

    app = FastAPI(title="AI Poster", version="0.1.0")

    from app.web.routes.jobs import router as jobs_router
    from app.web.routes.runs import router as runs_router

    app.include_router(jobs_router)
    app.include_router(runs_router)

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "backend": settings.intelligence_backend}

    return app


app = create_app()
