"""Shared fixtures for AFCS API integration tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from afcs_api.app import create_app
from afcs_api.db import Base, get_db
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def _db_engine():
    """Create a temporary file-based SQLite DB per test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def app(_db_engine) -> FastAPI:
    """Create the FastAPI app with DB overridden to the test engine."""

    def _test_get_db():
        session = Session(_db_engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    application = create_app()
    application.dependency_overrides[get_db] = _test_get_db
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Provide an HTTPX async client against the ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def cases_dir() -> Path:
    """Return the path to the cases directory."""
    return Path(__file__).resolve().parents[3] / "cases"
