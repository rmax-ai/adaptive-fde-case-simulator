"""Action execution and schema routes."""

from __future__ import annotations

import uuid

from afcs_domain import InvalidActionError, PreconditionError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.schemas import (
    ActionSchemaResponse,
    AvailableActionsResponse,
    ExecuteActionRequest,
    ExecuteActionResponse,
)
from afcs_api.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions/{session_id}/actions", tags=["actions"])


@router.get("/schema", response_model=AvailableActionsResponse)
def get_action_schemas(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> AvailableActionsResponse:
    """Return available actions with parameter schemas."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    available = service.get_available_actions(record)
    actions = [ActionSchemaResponse(**a) for a in available]
    return AvailableActionsResponse(actions=actions)


@router.post("", response_model=ExecuteActionResponse)
def execute_action(
    session_id: uuid.UUID,
    body: ExecuteActionRequest,
    db: SASession = Depends(get_db),  # noqa: B008
) -> ExecuteActionResponse:
    """Execute an action in the session."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        event_record, updated_session = service.execute_action(
            record, body.action_type, body.params
        )
    except PreconditionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidActionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    effects = (
        event_record.payload.get("effects", []) if isinstance(event_record.payload, dict) else []
    )
    return ExecuteActionResponse(
        event_id=event_record.id,
        sequence=event_record.sequence,
        event_type=event_record.event_type,
        new_state=service.get_visible_state(updated_session),
        effects=effects,
    )
