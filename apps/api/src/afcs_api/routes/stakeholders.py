"""Stakeholder conversation routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.schemas import (
    StakeholderInfo,
    StakeholderListResponse,
    StakeholderMessageRequest,
    StakeholderMessageResponse,
)
from afcs_api.services.session_service import SessionService

router = APIRouter(
    prefix="/api/v1/sessions/{session_id}/stakeholders",
    tags=["stakeholders"],
)


@router.get("", response_model=StakeholderListResponse)
def list_stakeholders(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> StakeholderListResponse:
    """List stakeholders with their roles and qualitative trust signals."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stakeholders = service.get_stakeholders(record)
    items = [StakeholderInfo(**s) for s in stakeholders]
    return StakeholderListResponse(stakeholders=items)


@router.post(
    "/{stakeholder_id}/messages",
    response_model=StakeholderMessageResponse,
)
def send_stakeholder_message(
    session_id: uuid.UUID,
    stakeholder_id: str,
    body: StakeholderMessageRequest,
    db: SASession = Depends(get_db),  # noqa: B008
) -> StakeholderMessageResponse:
    """Send a message to a stakeholder and get their response."""
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = service.send_stakeholder_message(
            record,
            stakeholder_id,
            body.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StakeholderMessageResponse(**result)
