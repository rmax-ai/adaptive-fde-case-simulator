"""Event stream routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.schemas import EventResponse, PaginatedEventsResponse
from afcs_api.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions/{session_id}/events", tags=["events"])


@router.get("", response_model=PaginatedEventsResponse)
def get_events(
    session_id: uuid.UUID,
    from_sequence: int = Query(default=0, ge=0, alias="from_sequence"),
    limit: int = Query(default=50, ge=1, le=200),
    db: SASession = Depends(get_db),  # noqa: B008
) -> PaginatedEventsResponse:
    """Get the event stream for a session."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    events = service.get_events(session_id, from_sequence=from_sequence, limit=limit)
    total = service.count_events(session_id)

    items = [
        EventResponse(
            id=e.id,
            session_id=e.session_id,
            sequence=e.sequence,
            event_type=e.event_type,
            actor_type=e.actor_type,
            actor_id=e.actor_id,
            payload=e.payload,
            pre_state_hash=e.pre_state_hash,
            post_state_hash=e.post_state_hash,
            created_at=e.created_at,
        )
        for e in events
    ]

    return PaginatedEventsResponse(
        items=items,
        total=total,
        from_sequence=from_sequence,
        limit=limit,
    )
