# app/core/db.py
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# --- Connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # Dev fallback (file-based SQLite). For Postgres set:
    # export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/ace"
    "sqlite:///./ace_dev.db",
)

# For SQLite we need check_same_thread False
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=({"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}),
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Non-FastAPI contexts (scripts, services)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
