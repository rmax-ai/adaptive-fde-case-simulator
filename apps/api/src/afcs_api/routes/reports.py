"""Final recommendation submission route."""

from __future__ import annotations

import uuid

from afcs_domain import InvalidActionError, PreconditionError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.schemas import (
    ExecuteActionResponse,
    SubmitFinalRecommendationRequest,
)
from afcs_api.services.session_service import SessionService

router = APIRouter(
    prefix="/api/v1/sessions/{session_id}/final-recommendation",
    tags=["reports"],
)


@router.post("", response_model=ExecuteActionResponse)
def submit_final_recommendation(
    session_id: uuid.UUID,
    body: SubmitFinalRecommendationRequest,
    db: SASession = Depends(get_db),  # noqa: B008
) -> ExecuteActionResponse:
    """Submit the final recommendation to close the engagement."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        event_record, updated_session = service.submit_final_recommendation(
            session=record,
            summary=body.summary,
            recommendation=body.recommendation,
            justification=body.justification,
            next_steps=body.next_steps,
        )
    except PreconditionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ExecuteActionResponse(
        event_id=event_record.id,
        sequence=event_record.sequence,
        event_type=event_record.event_type,
        new_state=service.get_visible_state(updated_session),
        effects=[],
    )
