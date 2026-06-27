"""Integration tests: artifact listing and retrieval."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_artifacts(client: AsyncClient):
    """List artifacts should return the case's visible artifacts."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/sessions/{session_id}/artifacts")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "artifacts" in data

    # The wrong_use_case v1 has one visible artifact (system-architecture)
    assert len(data["artifacts"]) >= 1

    artifact = data["artifacts"][0]
    assert "id" in artifact
    assert "type" in artifact
    assert "name" in artifact


@pytest.mark.asyncio
async def test_get_artifact_by_id(client: AsyncClient):
    """Get a specific artifact by its ID."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    # First list to get the ID
    list_resp = await client.get(f"/api/v1/sessions/{session_id}/artifacts")
    artifacts = list_resp.json()["artifacts"]

    if artifacts:
        artifact_id = artifacts[0]["id"]
        response = await client.get(
            f"/api/v1/sessions/{session_id}/artifacts/{artifact_id}"
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == artifact_id
        assert "type" in data
        assert "name" in data


@pytest.mark.asyncio
async def test_get_artifact_not_found(client: AsyncClient):
    """Get a non-existent artifact should return 404."""
    create_resp = await client.post(
        "/api/v1/sessions",
        json={"case_id": "wrong_use_case"},
    )
    session_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/sessions/{session_id}/artifacts/nonexistent-artifact"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_artifacts_on_nonexistent_session(client: AsyncClient):
    """Listing artifacts on a non-existent session should return 404."""
    response = await client.get(
        "/api/v1/sessions/00000000-0000-0000-0000-000000000000/artifacts"
    )
    assert response.status_code == 404
