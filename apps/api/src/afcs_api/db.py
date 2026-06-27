"""SQLAlchemy 2.0 async engine, session factory, and dependency."""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

# ---------------------------------------------------------------------------
# Database URL — override via DATABASE_URL env var
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///afcs.db",
)

# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all API ORM models."""


# ---------------------------------------------------------------------------
# Engine & session factory (sync for simplicity; matches test infra)
# ---------------------------------------------------------------------------

engine = create_engine(DATABASE_URL, echo=False)


def create_session() -> Session:
    """Return a new sync Session bound to the global engine."""
    return Session(engine)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session per request."""
    session = create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
