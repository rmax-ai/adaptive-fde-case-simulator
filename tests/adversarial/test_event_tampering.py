"""Test event tampering attempts."""

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
async def test_tamper_event_via_put(client: AsyncClient):
    """Blocked: Attempt to modify an event via PUT (no such route)."""
    session_id = await _create_session(client)
    if not session_id:
        return

    fake_event_id = str(uuid.uuid4())
    resp = await client.put(
        f"/api/v1/sessions/{session_id}/events/{fake_event_id}",
        json={"payload": {"tampered": True}},
    )
    assert resp.status_code in (405, 404, 403, 400), (
        f"Unexpected status for PUT on events: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_tamper_event_via_delete(client: AsyncClient):
    """Blocked: Attempt to delete an event (no such route)."""
    session_id = await _create_session(client)
    if not session_id:
        return

    fake_event_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/v1/sessions/{session_id}/events/{fake_event_id}")
    assert resp.status_code in (405, 404, 403, 400), (
        f"Unexpected status for DELETE on events: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_tamper_session_via_patch(client: AsyncClient):
    """Blocked: Attempt to PATCH a session to change its status directly."""
    session_id = await _create_session(client)
    if not session_id:
        return

    resp = await client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"status": "completed", "score": 100},
    )
    assert resp.status_code in (405, 404, 403, 400), (
        f"Unexpected status for PATCH on session: {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_tamper_evaluation_score(client: AsyncClient):
    """Blocked: Attempt to directly post to evaluation endpoint."""
    session_id = await _create_session(client)
    if not session_id:
        return

    resp = await client.post(
        f"/api/v1/sessions/{session_id}/evaluation",
        json={
            "overall_score": 100.0,
            "dimensions": [{"name": "test", "score": 100.0}],
        },
    )
    assert resp.status_code in (405, 403, 404, 400), (
        f"Unexpected status for POST on evaluation: {resp.status_code}"
    )
