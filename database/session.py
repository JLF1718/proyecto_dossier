"""
Database Session Management
============================
Provides a SQLAlchemy engine and session factory.
Database URL defaults to SQLite (``database/qa_platform.db``) and can be
overridden via the DATABASE_URL environment variable for PostgreSQL/MySQL.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from backend.config import get_settings

_settings = get_settings()

# Resolve relative SQLite path to absolute so it always lands in the project root
_db_url = _settings.database_url
if _db_url.startswith("sqlite:///./"):
    _relative = _db_url[len("sqlite:///./"):]
    _abs = _settings.project_root / _relative
    _abs.parent.mkdir(parents=True, exist_ok=True)
    _db_url = f"sqlite:///{_abs}"

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if "sqlite" in _db_url else {},
    echo=_settings.debug,
)

# Enable WAL mode for SQLite to support concurrent readers + one writer
if "sqlite" in _db_url:
    @event.listens_for(engine, "connect")
    def _set_wal(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA journal_mode=WAL;")
        dbapi_connection.execute("PRAGMA foreign_keys=ON;")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db() -> Session:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined by ORM models."""
    from database import models  # noqa: F401 — ensures models are registered
    Base.metadata.create_all(bind=engine)
