"""Integration tests: stakeholder listing and messaging."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_stakeholders(client: AsyncClient):
    """List stakeholders should return case stakeholders with trust signals."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/sessions/{session_id}/stakeholders")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "stakeholders" in data
    stakeholders = data["stakeholders"]

    # wrong_use_case v1 has at least 1 stakeholder
    assert len(stakeholders) >= 1

    stakeholder = stakeholders[0]
    assert "id" in stakeholder
    assert "role" in stakeholder
    assert "trust_signal" in stakeholder

    # Trust signal must be qualitative, never numeric
    assert stakeholder["trust_signal"] in (
        "cooperative",
        "hesitant",
        "blocked",
        "escalating",
        "awaiting_evidence",
    )

    # The cto stakeholder starts with trust_initial=5 (score 50) -> awaiting_evidence
    if stakeholder["id"] == "cto":
        assert stakeholder["trust_signal"] == "awaiting_evidence"
        assert stakeholder["role"] == "Chief Technology Officer"


@pytest.mark.asyncio
async def test_list_stakeholders_nonexistent_session(client: AsyncClient):
    """Listing stakeholders on a non-existent session should return 404."""
    response = await client.get(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000/stakeholders",
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_stakeholder_message(client: AsyncClient):
    """Sending a message to a stakeholder should return a response."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/sessions/{session_id}/stakeholders/cto/messages",
        json={"message": "Can you tell me about the current system architecture?"},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["stakeholder_id"] == "cto"
    assert "message" in data
    assert len(data["message"]) > 0
    assert "tone" in data
    assert isinstance(data["disclosed_fact_ids"], list)

    # At initial trust level (50), tone should be hesitant
    assert data["tone"] == "hesitant"


@pytest.mark.asyncio
async def test_send_message_nonexistent_stakeholder(client: AsyncClient):
    """Sending a message to a non-existent stakeholder should return 404."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/sessions/{session_id}/stakeholders/nonexistent/messages",
        json={"message": "Hello?"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_message_nonexistent_session(client: AsyncClient):
    """Sending a message on a non-existent session should return 404."""
    response = await client.post(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000/stakeholders/cto/messages",
        json={"message": "Hello?"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trust_signal_updates_after_messaging(client: AsyncClient):
    """Trust signal should update after sending messages."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # Send a few messages that change trust
    response = await client.post(
        f"/api/v1/sessions/{session_id}/stakeholders/cto/messages",
        json={"message": "Question 1"},
    )
    assert response.status_code == 200

    # After hesitant message (trust_delta=-3, from 50 -> 47),
    # signal should still be awaiting_evidence
    list_resp = await client.get(f"/api/v1/sessions/{session_id}/stakeholders")
    cto = next(s for s in list_resp.json()["stakeholders"] if s["id"] == "cto")
    assert cto["trust_signal"] in (
        "awaiting_evidence",
        "hesitant",
        "blocked",
    )
