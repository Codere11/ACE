# app/services/bootstrap_db.py
from app.core.db import Base, engine
from app.models import orm  # noqa: F401  (import models so mappers register)


def create_all() -> None:
    """Create tables if they don't exist (MVP)."""
    Base.metadata.create_all(bind=engine)
