"""Integration tests: action execution, precondition validation, sequence tracking."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_action_schemas(client: AsyncClient):
    """GET action schemas should return available actions with parameter schemas."""
    # Create a session first
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Get action schemas
    response = await client.get(f"/api/v1/sessions/{session_id}/actions/schema")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "actions" in data
    assert len(data["actions"]) > 0

    # Each action should have the required schema fields
    first_action = data["actions"][0]
    assert "action_type" in first_action
    assert "description" in first_action
    assert "parameters_schema" in first_action
    assert "time_cost" in first_action


@pytest.mark.asyncio
async def test_execute_action(client: AsyncClient):
    """Execute a valid action and verify the response has event_id, sequence, new_state."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "action_type": "register_assumption",
            "params": {
                "description": "Users will adopt the new system within 2 weeks",
                "category": "business",
            },
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "event_id" in data
    assert "sequence" in data
    assert "new_state" in data
    assert data["sequence"] == 0  # first event


@pytest.mark.asyncio
async def test_action_sequence_tracking(client: AsyncClient):
    """Each subsequent action should increment the sequence number."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # First action
    resp1 = await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "action_type": "register_assumption",
            "params": {"description": "Assumption 1"},
        },
    )
    assert resp1.status_code == 200
    assert resp1.json()["sequence"] == 0

    # Second action
    resp2 = await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "action_type": "register_risk",
            "params": {"description": "Risk 1", "impact": "high"},
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["sequence"] == 1

    # Third action
    resp3 = await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "action_type": "register_assumption",
            "params": {"description": "Assumption 2"},
        },
    )
    assert resp3.status_code == 200
    assert resp3.json()["sequence"] == 2


@pytest.mark.asyncio
async def test_action_precondition_failure(client: AsyncClient):
    """Executing an action with unknown type should fail with 400."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Try executing an unknown action type
    response = await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "action_type": "nonexistent_action",
            "params": {},
        },
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_action_on_nonexistent_session(client: AsyncClient):
    """Executing an action on a non-existent session should return 404."""
    response = await client.post(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000/actions",
        json={
            "action_type": "register_assumption",
            "params": {"description": "test"},
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_final_recommendation_endpoint(client: AsyncClient):
    """POST /final-recommendation should work as an API endpoint."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # The endpoint exists and returns a proper response (phase gate prevents execution)
    response = await client.post(
        f"/api/v1/sessions/{session_id}/final-recommendation",
        json={
            "summary": "Found GenAI is wrong solution",
            "recommendation": "Use rule-based automation",
            "justification": "Cost-effective and proven",
            "next_steps": ["Implement rule engine", "Train team"],
        },
    )
    # Phase gate prevents submission (need reporting phase), returns 400
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_submit_final_recommendation_via_actions(client: AsyncClient):
    """submit_final_recommendation action respects phase gates."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Advance to architecture phase
    await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={"action_type": "define_baseline", "params": {"description": "baseline"}},
    )
    await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={"action_type": "select_architecture", "params": {"name": "arch1"}},
    )

    # submit_final_recommendation requires 'reporting' phase
    response = await client.post(
        f"/api/v1/sessions/{session_id}/actions",
        json={
            "action_type": "submit_final_recommendation",
            "params": {
                "summary": "Summary",
                "recommendation": "Recommendation",
                "justification": "Justification",
            },
        },
    )
    # Phase gate should block: requires 'reporting', current is 'architecture'
    assert response.status_code == 400, response.text
    detail = response.json()["detail"].lower()
    assert "phase" in detail or "reporting" in detail
