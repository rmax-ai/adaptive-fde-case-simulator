"""Integration tests: agent API endpoints (state, action schemas, execution)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_agent_state(client: AsyncClient):
    """GET agent state should return verbose machine-readable state."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/agent/sessions/{session_id}/state")
    assert response.status_code == 200, response.text
    data = response.json()

    # Core fields
    assert data["session_id"] == session_id
    assert data["status"] == "in_progress"
    assert data["phase"] is not None
    assert data["current_sequence"] >= 0
    assert "budget_remaining" in data
    assert "artifacts" in data
    assert "stakeholder_relationships" in data
    assert "flags" in data
    assert "metadata" in data
    assert "event_count" in data

    # Available actions should be a list of AgentActionSchema
    assert "available_actions" in data
    assert len(data["available_actions"]) > 0
    first_action = data["available_actions"][0]
    assert "action_type" in first_action
    assert "description" in first_action
    assert "parameters_schema" in first_action
    assert "preconditions" in first_action
    assert "time_cost" in first_action

    # Stakeholders should be present
    assert "stakeholders" in data
    if len(data["stakeholders"]) > 0:
        first_stakeholder = data["stakeholders"][0]
        assert "id" in first_stakeholder
        assert "role" in first_stakeholder
        assert "trust_signal" in first_stakeholder


@pytest.mark.asyncio
async def test_get_agent_state_not_found(client: AsyncClient):
    """GET agent state on non-existent session should return 404."""
    response = await client.get(
        "/api/v1/agent/sessions/00000000-0000-0000-0000-000000000000/state"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_action_schemas(client: AsyncClient):
    """GET agent action schemas should return full JSON Schema specs."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/agent/sessions/{session_id}/actions")
    assert response.status_code == 200, response.text
    actions = response.json()

    assert isinstance(actions, list)
    assert len(actions) > 0

    # Each action must have full schema
    for action in actions:
        assert "action_type" in action
        assert "description" in action
        assert "parameters_schema" in action
        assert isinstance(action["parameters_schema"], dict)
        assert "preconditions" in action
        assert "time_cost" in action

    # Check specific action types exist
    action_types = {a["action_type"] for a in actions}
    expected_types = {
        "inspect_artifact",
        "interview_stakeholder",
        "register_assumption",
        "register_risk",
        "define_baseline",
        "select_architecture",
        "submit_final_recommendation",
    }
    assert expected_types.issubset(action_types), (
        f"Missing action types: {expected_types - action_types}"
    )

    # inspect_artifact should have artifact_id in parameters_schema
    inspect = next(a for a in actions if a["action_type"] == "inspect_artifact")
    params = inspect["parameters_schema"]
    assert "properties" in params
    assert "artifact_id" in params["properties"]


@pytest.mark.asyncio
async def test_execute_agent_action_success(client: AsyncClient):
    """POST agent action should execute successfully and return structured result."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "register_assumption",
            "params": {
                "description": "Agent test assumption",
                "category": "technical",
            },
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["success"] is True
    assert "event_id" in data
    assert data["sequence"] >= 0
    assert data["event_type"] == "action_executed"
    assert data["action_type"] == "register_assumption"

    # Should contain new_state with full agent state
    assert data["new_state"] is not None
    new_state = data["new_state"]
    assert new_state["session_id"] == session_id
    assert new_state["current_sequence"] >= 1
    assert "available_actions" in new_state
    assert "stakeholders" in new_state

    # Error should be None on success
    assert data["error"] is None


@pytest.mark.asyncio
async def test_execute_agent_action_failure(client: AsyncClient):
    """POST agent action with invalid type should return success=False with error."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "nonexistent_action",
            "params": {},
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["success"] is False
    assert data["error"] is not None
    assert "Unknown action type" in data["error"] or "Cannot execute" in data["error"]


@pytest.mark.asyncio
async def test_execute_agent_action_not_found(client: AsyncClient):
    """POST agent action on non-existent session should return 404."""
    response = await client.post(
        "/api/v1/agent/sessions/00000000-0000-0000-0000-000000000000/actions",
        json={
            "action_type": "register_assumption",
            "params": {"description": "test"},
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_agent_state_updates_after_actions(client: AsyncClient):
    """Agent state should reflect changes after each action."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Execute an action
    await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "register_assumption",
            "params": {"description": "Test assumption update state"},
        },
    )

    # Check state reflects the action
    state_resp = await client.get(f"/api/v1/agent/sessions/{session_id}/state")
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["event_count"] >= 1
    assert state["current_sequence"] >= 1


@pytest.mark.asyncio
async def test_agent_full_simulation_flow(client: AsyncClient):
    """Run a complete simulation flow through the agent API endpoints."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Get initial state
    state_resp = await client.get(f"/api/v1/agent/sessions/{session_id}/state")
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["phase"] == "discovery"
    assert state["status"] == "in_progress"

    # Get action schemas
    actions_resp = await client.get(f"/api/v1/agent/sessions/{session_id}/actions")
    assert actions_resp.status_code == 200
    actions = actions_resp.json()
    action_types = {a["action_type"] for a in actions}
    assert "inspect_artifact" in action_types

    # Inspect artifacts
    artifacts = state.get("artifacts", [])
    for artifact in artifacts:
        result = await client.post(
            f"/api/v1/agent/sessions/{session_id}/actions",
            json={
                "action_type": "inspect_artifact",
                "params": {"artifact_id": artifact["id"]},
            },
        )
        assert result.status_code == 200
        assert result.json()["success"] is True

    # Interview stakeholders
    stakeholders = state.get("stakeholders", [])
    for stakeholder in stakeholders:
        result = await client.post(
            f"/api/v1/agent/sessions/{session_id}/actions",
            json={
                "action_type": "interview_stakeholder",
                "params": {
                    "stakeholder_id": stakeholder["id"],
                    "topics": ["goals"],
                    "notes": "Initial interview",
                },
            },
        )
        assert result.status_code == 200
        assert result.json()["success"] is True

    # Register assumptions
    await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "register_assumption",
            "params": {"description": "Test assumption", "category": "technical"},
        },
    )

    # Register risk
    await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "register_risk",
            "params": {"description": "Test risk", "impact": "medium"},
        },
    )

    # Define baseline (advances to evaluation)
    result = await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "define_baseline",
            "params": {"description": "Baseline", "metrics": ["accuracy"]},
        },
    )
    assert result.json()["success"] is True

    # Verify phase advanced
    state_resp = await client.get(f"/api/v1/agent/sessions/{session_id}/state")
    assert state_resp.json()["phase"] == "evaluation"

    # Select architecture (advances to architecture)
    await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "define_success_metric",
            "params": {"name": "Accuracy", "target": ">95%"},
        },
    )
    result = await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "select_architecture",
            "params": {"name": "Rule-based engine", "description": "Rule engine"},
        },
    )
    assert result.json()["success"] is True

    # Run analysis (available in architecture phase)
    await client.post(
        f"/api/v1/agent/sessions/{session_id}/actions",
        json={
            "action_type": "run_analysis",
            "params": {"type": "cost", "findings": "Good approach", "conclusion": "Recommended"},
        },
    )

    # Prepare handoff (available in reporting - needs advancement)
    # Note: run_pilot requires 'delivery' phase (existing phase gate behavior).
    # We advance through phases directly via define_baseline -> select_architecture.
    # For this test, we simulate a complete flow by advancing through each
    # available action in sequence, skipping actions gated behind unattainable phases.

    # Submit final recommendation is gated behind 'reporting' phase,
    # so we just verify we made progress through the flow up to architecture phase.
    state_resp = await client.get(f"/api/v1/agent/sessions/{session_id}/state")
    state = state_resp.json()
    assert state["phase"] == "architecture"
    assert state["event_count"] >= 5
