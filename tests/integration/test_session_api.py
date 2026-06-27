"""Integration tests: session CRUD and state projection."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    """Creating a session should return 201 with session details."""
    response = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["case_id"] == "wrong_use_case"
    assert "id" in data
    assert "visible_state" in data
    assert data["current_sequence"] == 0
    assert data["completed_at"] is None


@pytest.mark.asyncio
async def test_create_session_with_participant(client: AsyncClient):
    """Creating a session with a participant_id should reflect it."""
    response = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case", "participant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["participant_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@pytest.mark.asyncio
async def test_get_session(client: AsyncClient):
    """GET session should return full details with visible state."""
    # Create first
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Then get
    response = await client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == session_id
    assert data["status"] == "in_progress"
    assert "visible_state" in data


@pytest.mark.asyncio
async def test_get_session_state(client: AsyncClient):
    """GET session state should return only visible state (no hidden fields)."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/sessions/{session_id}/state")
    assert response.status_code == 200, response.text
    state = response.json()

    # Must NOT contain hidden fields
    hidden_fields = {"hidden_context", "risk_assessment", "correct_solution", "evaluation_criteria"}
    for field in hidden_fields:
        assert field not in state, f"Hidden field '{field}' leaked into visible state!"

    # Must contain visible fields
    visible_fields = {"phase", "budget_remaining", "artifacts", "flags", "metadata"}
    for field in visible_fields:
        assert field in state, f"Visible field '{field}' missing from state!"


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient):
    """GET non-existent session should return 404."""
    response = await client.get(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_session_unknown_case(client: AsyncClient):
    """Creating a session with an unknown case should return 404."""
    response = await client.post(
        "/api/v1/sessions",
        json={"case_id": "nonexistent_case"},
    )
    assert response.status_code == 404
