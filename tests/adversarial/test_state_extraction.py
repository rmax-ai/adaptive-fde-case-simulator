"""Test hidden state extraction attempts."""

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
async def test_extract_internal_state(client: AsyncClient):
    """Attempt to access internal session state not visible to participants."""
    session_id = await _create_session(client)
    if not session_id:
        return

    resp = await client.get(f"/api/v1/sessions/{session_id}/state?include_internal=true")
    assert resp.status_code in (200, 400, 422, 403), f"Unexpected: {resp.status_code}"
    if resp.status_code == 200:
        data = resp.json()
        internal_keys = {"pre_state_hash", "post_state_hash", "full_state", "internal"}
        for key in internal_keys:
            assert key not in data, f"Internal state key '{key}' leaked"


@pytest.mark.asyncio
async def test_extract_full_event_payload(client: AsyncClient):
    """Attempt to extract hidden payload data from events."""
    session_id = await _create_session(client)
    if not session_id:
        return

    resp = await client.get(f"/api/v1/sessions/{session_id}/events?from_sequence=0&limit=200")
    assert resp.status_code in (200, 404, 403), f"Unexpected: {resp.status_code}"
    if resp.status_code == 200:
        data = resp.json()
        for event in data.get("items", []):
            payload = event.get("payload", {})
            if isinstance(payload, dict):
                payload_str = str(payload).lower()
                assert "system prompt" not in payload_str, "Event payload leaked system prompt"
                assert "you are a helpful" not in payload_str, (
                    "Event payload leaked base instructions"
                )


@pytest.mark.asyncio
async def test_extract_database_schema(client: AsyncClient):
    """Attempt to extract database schema through error messages."""
    session_id = str(uuid.uuid4())  # Non-existent session

    resp = await client.get(f"/api/v1/sessions/{session_id}/state")
    assert resp.status_code == 404, f"Expected 404 for non-existent session, got {resp.status_code}"
    body_text = str(resp.json()).lower()
    sql_indicators = ["select", "from", "table", "column", "session_records"]
    for indicator in sql_indicators:
        assert indicator not in body_text, f"Error response leaked SQL: '{indicator}' found"
