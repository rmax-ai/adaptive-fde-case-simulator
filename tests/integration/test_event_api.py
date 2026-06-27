"""Integration tests: event stream."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_events_empty(client: AsyncClient):
    """A fresh session should have no events."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/sessions/{session_id}/events")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "items" in data
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_events_after_actions(client: AsyncClient):
    """Events should be recorded after executing actions."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Execute two actions
    await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "action_type": "register_assumption",
            "params": {"description": "Test assumption"},
        },
    )
    await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "action_type": "register_risk",
            "params": {"description": "Test risk"},
        },
    )

    # Get events
    response = await client.get(f"/api/v1/sessions/{session_id}/events")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Events should be in order
    assert data["items"][0]["sequence"] == 0
    assert data["items"][1]["sequence"] == 1
    assert data["items"][0]["event_type"] == "action_executed"
    assert data["items"][1]["event_type"] == "action_executed"


@pytest.mark.asyncio
async def test_get_events_pagination(client: AsyncClient):
    """Events should support from_sequence and limit query parameters."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Execute three actions
    for i in range(3):
        await client.post(
            f"/api/v1/sessions/{session_id}/actions",
            json={
                "action_type": "register_assumption",
                "params": {"description": f"Assumption {i}"},
            },
        )

    # Get events from sequence 1, limit 1
    response = await client.get(
        f"/api/v1/sessions/{session_id}/events?from_sequence=1&limit=1"
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["sequence"] == 1
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_events_on_nonexistent_session(client: AsyncClient):
    """Getting events on a non-existent session should return 404."""
    response = await client.get(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000/events"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint should return 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "afcs-api"
