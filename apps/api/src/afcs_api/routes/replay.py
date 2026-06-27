"""Replay timeline route — chronological events with state diffs."""

from __future__ import annotations

import uuid

from afcs_simulation_engine import ReplayService
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.schemas import ReplayEventResponse, ReplayTimelineResponse
from afcs_api.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions/{session_id}/replay", tags=["replay"])


@router.get("", response_model=ReplayTimelineResponse)
def get_replay_timeline(
    session_id: uuid.UUID,
    dimension: str | None = Query(
        default=None,
        description="Optional dimension filter (e.g. 'discovery', 'technical')",
    ),
    db: SASession = Depends(get_db),  # noqa: B008
) -> ReplayTimelineResponse:
    """Get chronological replay timeline with state diffs for a session.

    Returns all events annotated with computed state transitions,
    relevant evaluation dimensions, and human-readable summaries.
    """
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    events = service.get_events(session_id, from_sequence=0, limit=500)
    replay_service = ReplayService()

    timeline = replay_service.build_timeline(
        events=[e.to_domain_event() for e in events],
        dimension_filter=dimension,
    )

    return ReplayTimelineResponse(
        session_id=str(session_id),
        events=[ReplayEventResponse(**entry) for entry in timeline],
        total_events=len(timeline),
        available_dimensions=replay_service.get_available_dimensions(),
    )
