from __future__ import annotations

from typing import Optional

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.settings import AppSettings

_settings: Optional[AppSettings] = None
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def init_state(settings: AppSettings, engine: Engine, session_factory: sessionmaker[Session]) -> None:
    global _settings, _engine, _SessionLocal
    _settings = settings
    _engine = engine
    _SessionLocal = session_factory


def get_settings() -> AppSettings:
    if _settings is None:
        raise RuntimeError("App state not initialized")
    return _settings


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("App state not initialized")
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        raise RuntimeError("App state not initialized")
    return _SessionLocal
