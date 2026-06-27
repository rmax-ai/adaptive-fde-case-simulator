"""Artifact inspection routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.schemas import ArtifactListResponse, ArtifactResponse
from afcs_api.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions/{session_id}/artifacts", tags=["artifacts"])


@router.get("", response_model=ArtifactListResponse)
def list_artifacts(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> ArtifactListResponse:
    """List visible artifacts for the session."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    artifacts = service.get_visible_artifacts(record)
    items = [ArtifactResponse(**a) for a in artifacts]
    return ArtifactListResponse(artifacts=items)


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(
    session_id: uuid.UUID,
    artifact_id: str,
    db: SASession = Depends(get_db),  # noqa: B008
) -> ArtifactResponse:
    """Get a specific artifact's content."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    artifact = service.get_artifact(record, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return ArtifactResponse(**artifact)
