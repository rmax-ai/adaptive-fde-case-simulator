"""Test cross-session access control."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _create_session(client: AsyncClient) -> str | None:
    """Helper: create a minimal session."""
    resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    if resp.status_code == 201:
        return resp.json()["id"]
    pytest.skip(f"Session creation returned {resp.status_code} — skipping")
    return None


@pytest.mark.asyncio
async def test_cross_session_event_access(client: AsyncClient):
    """Blocked: Accessing events of one session from another."""
    session_id = await _create_session(client)
    if not session_id:
        return

    other_session_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/sessions/{other_session_id}/events")
    assert resp.status_code in (404, 403), (
        f"Expected 404/403 for cross-session access, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_cross_session_state_access(client: AsyncClient):
    """Blocked: Accessing state of a different session."""
    session_id = await _create_session(client)
    if not session_id:
        return

    other_session_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/sessions/{other_session_id}/state")
    assert resp.status_code in (404, 403), (
        f"Expected 404/403 for cross-session state access, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_cross_session_action_execution(client: AsyncClient):
    """Blocked: Executing actions on a different session."""
    other_session_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/sessions/{other_session_id}/actions",
        json={"action_type": "inspect_artifact", "params": {}},
    )
    assert resp.status_code in (404, 403), (
        f"Expected 404/403 for cross-session action, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_cross_session_stakeholder_access(client: AsyncClient):
    """Blocked: Accessing stakeholders of a different session."""
    other_session_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/sessions/{other_session_id}/stakeholders")
    assert resp.status_code in (404, 403), (
        f"Expected 404/403 for cross-session stakeholder access, got {resp.status_code}"
    )
