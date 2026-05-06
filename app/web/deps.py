from sqlalchemy.orm import Session

from app.core.settings import AppSettings
from app.web import state


def get_settings():
    return state.get_settings()


def get_db():
    factory = state.get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
