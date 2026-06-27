"""Integration tests for evaluation API endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from afcs_api.app import create_app
from afcs_api.db import Base, get_db
from afcs_api.services.session_service import SessionService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _db_engine():
    """Create a temporary file-based SQLite DB per test."""
    import tempfile

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
    return Path(__file__).resolve().parents[2] / "cases"


@pytest.fixture
def _test_db(_db_engine):
    """Provide a SQLAlchemy Session connected to the test DB."""
    session = Session(_db_engine)
    yield session
    session.close()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_first_case_id(cases_dir: Path) -> str:
    """Return the case_id from the first available case directory."""
    from afcs_case_schema.loader import load_case_dir

    for child in sorted(cases_dir.iterdir()):
        if child.is_dir():
            try:
                cases = load_case_dir(child)
                if cases:
                    return cases[0].metadata.case_id
            except (FileNotFoundError, ValueError, NotADirectoryError):
                continue
    raise RuntimeError(f"No valid cases found in {cases_dir}")


def _complete_session_via_service(case_id: str, _test_db: Session) -> str:
    """Create and complete a session using the service directly.

    Returns the session_id (as string) of the completed session.
    """
    service = SessionService(_test_db)
    record, _ = service.create_session(case_id)
    session_id = str(record.id)

    from uuid import UUID

    from afcs_api.models import SessionRecord
    from sqlalchemy import update

    _test_db.execute(
        update(SessionRecord).where(SessionRecord.id == UUID(session_id)).values(status="completed")
    )
    _test_db.commit()

    return session_id


# ── Tests ────────────────────────────────────────────────────────────────────

_EVALUATOR_HEADERS = {"X-Actor-Role": "evaluator"}


@pytest.mark.asyncio
async def test_evaluation_returns_403_when_session_not_completed(
    client: AsyncClient, cases_dir: Path
):
    """GET /evaluation on an in-progress session should return 403."""
    case_id = _get_first_case_id(cases_dir)

    resp = await client.post("/api/v1/sessions", json={"case_id": case_id})
    assert resp.status_code == 201, f"Failed to create session: {resp.text}"
    session_id = resp.json()["id"]

    resp = await client.get(
        f"/api/v1/sessions/{session_id}/evaluation",
        headers=_EVALUATOR_HEADERS,
    )
    assert resp.status_code == 403, (
        f"Expected 403 for non-completed session, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "detail" in data
    assert "not completed" in data["detail"].lower()


@pytest.mark.asyncio
async def test_report_returns_403_when_session_not_completed(client: AsyncClient, cases_dir: Path):
    """GET /report on an in-progress session should return 403."""
    case_id = _get_first_case_id(cases_dir)

    resp = await client.post("/api/v1/sessions", json={"case_id": case_id})
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    resp = await client.get(
        f"/api/v1/sessions/{session_id}/report",
        headers=_EVALUATOR_HEADERS,
    )
    assert resp.status_code == 403, (
        f"Expected 403 for non-completed session, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "detail" in data
    assert "not completed" in data["detail"].lower()


@pytest.mark.asyncio
async def test_evaluation_returns_404_for_nonexistent_session(client: AsyncClient):
    """GET /evaluation on a non-existent session should return 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/sessions/{fake_id}/evaluation",
        headers=_EVALUATOR_HEADERS,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluation_triggers_on_completion(
    client: AsyncClient, cases_dir: Path, _test_db: Session
):
    """Evaluation should be accessible after session completion.

    Uses the service layer to create a session and mark it as completed,
    then verifies the evaluation/report endpoints return data.
    """
    case_id = _get_first_case_id(cases_dir)
    session_id = _complete_session_via_service(case_id, _test_db)

    # Now evaluation should work
    eval_resp = await client.get(
        f"/api/v1/sessions/{session_id}/evaluation",
        headers=_EVALUATOR_HEADERS,
    )
    assert eval_resp.status_code == 200, (
        "Expected 200 for evaluation after completion, "
        f"got {eval_resp.status_code}: {eval_resp.text}"
    )
    eval_data = eval_resp.json()
    assert eval_data["session_id"] == str(session_id)
    assert 0 <= eval_data["overall_score"] <= 100
    assert "dimensions" in eval_data

    # Check dimensions
    if eval_data["dimensions"]:
        for dim in eval_data["dimensions"]:
            assert "name" in dim
            assert "score" in dim

    # Check report
    report_resp = await client.get(
        f"/api/v1/sessions/{session_id}/report",
        headers=_EVALUATOR_HEADERS,
    )
    assert report_resp.status_code == 200, (
        f"Expected 200 for report, got {report_resp.status_code}: {report_resp.text}"
    )
    report_data = report_resp.json()
    assert report_data["session_id"] == str(session_id)
    assert "timeline" in report_data
    assert "artifacts_inspected" in report_data


@pytest.mark.asyncio
async def test_evaluation_returns_consistent_results(
    client: AsyncClient, cases_dir: Path, _test_db: Session
):
    """Calling evaluation twice on same session returns consistent results."""
    case_id = _get_first_case_id(cases_dir)
    session_id = _complete_session_via_service(case_id, _test_db)

    # Call evaluation twice
    resp1 = await client.get(
        f"/api/v1/sessions/{session_id}/evaluation",
        headers=_EVALUATOR_HEADERS,
    )
    assert resp1.status_code == 200
    resp2 = await client.get(
        f"/api/v1/sessions/{session_id}/evaluation",
        headers=_EVALUATOR_HEADERS,
    )
    assert resp2.status_code == 200

    data1 = resp1.json()
    data2 = resp2.json()
    assert data1["overall_score"] == data2["overall_score"]
    assert data1["session_id"] == data2["session_id"]
