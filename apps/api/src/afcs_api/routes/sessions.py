"""Session CRUD routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.schemas import CreateSessionRequest, SessionResponse
from afcs_api.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", status_code=201, response_model=SessionResponse)
def create_session(
    body: CreateSessionRequest,
    db: SASession = Depends(get_db),  # noqa: B008
) -> SessionResponse:
    """Create a new simulation session."""
    service = SessionService(db)

    try:
        record, visible_state = service.create_session(
            case_id=body.case_id,
            participant_id=body.participant_id,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SessionResponse(
        id=record.id,
        case_id=record.case_id,
        case_version=record.case_version,
        participant_id=record.participant_id,
        status=record.status,
        current_sequence=record.current_sequence,
        visible_state=visible_state,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> SessionResponse:
    """Get session details with visible state."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    visible_state = service.get_visible_state(record)
    return SessionResponse(
        id=record.id,
        case_id=record.case_id,
        case_version=record.case_version,
        participant_id=record.participant_id,
        status=record.status,
        current_sequence=record.current_sequence,
        visible_state=visible_state,
        started_at=record.started_at,
        completed_at=record.completed_at,
    )


@router.get("/{session_id}/state")
def get_session_state(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> dict:
    """Get only the visible state for a session."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    visible_state = service.get_visible_state(record)
    return visible_state
