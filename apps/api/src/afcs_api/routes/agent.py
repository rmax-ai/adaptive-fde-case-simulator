"""Dedicated agent API endpoints for machine consumption.

These endpoints are optimized for AI agent clients that need a single,
rich state representation with embedded action schemas, stakeholder info,
and structured action execution results.
"""

from __future__ import annotations

import uuid

from afcs_domain import InvalidActionError, PreconditionError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.models import SessionRecord
from afcs_api.schemas import (
    AgentActionResult,
    AgentActionSchema,
    AgentStateResponse,
    ExecuteActionRequest,
    StakeholderInfo,
)
from afcs_api.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/agent/sessions", tags=["agent"])


def _build_agent_state(
    service: SessionService,
    session_id: uuid.UUID,
    session_record: SessionRecord,
) -> AgentStateResponse:
    """Build a verbose AgentStateResponse from the current session state."""
    visible = service.get_visible_state(session_record)
    available_actions_raw = service.get_available_actions(session_record)
    stakeholders_raw = service.get_stakeholders(session_record)
    event_count = service.count_events(session_id)

    available_actions = [
        AgentActionSchema(
            action_type=a.get("action_type", ""),
            description=a.get("description", ""),
            parameters_schema=a.get("parameters_schema", {}),
            preconditions=a.get("preconditions", []),
            time_cost=a.get("time_cost", 10),
            budget_cost=a.get("budget_cost"),
        )
        for a in available_actions_raw
    ]

    stakeholders = [StakeholderInfo(**s) for s in stakeholders_raw]

    return AgentStateResponse(
        session_id=str(session_id),
        case_id=session_record.case_id,
        status=session_record.status,
        phase=visible.get("phase", "unknown"),
        current_sequence=session_record.current_sequence,
        budget_remaining=visible.get("budget_remaining", 0.0),
        artifacts=visible.get("artifacts", []),
        stakeholder_relationships=visible.get("stakeholder_relationships", {}),
        flags=visible.get("flags", {}),
        metadata=visible.get("metadata", {}),
        available_actions=available_actions,
        stakeholders=stakeholders,
        event_count=event_count,
    )


@router.get("/{session_id}/state", response_model=AgentStateResponse)
def get_agent_state(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> AgentStateResponse:
    """Get full verbose machine-readable state for AI agent consumption.

    Returns session metadata, visible state, available actions with full
    JSON Schema parameter specs, stakeholders, and event count in a single
    response — optimized for agent decision-making.
    """
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return _build_agent_state(service, session_id, record)


@router.get("/{session_id}/actions", response_model=list[AgentActionSchema])
def get_agent_action_schemas(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> list[AgentActionSchema]:
    """Get available action schemas with full JSON Schema parameter specs.

    Each action includes its type, description, parameters_schema (full
    JSON Schema), precondition status, time cost, and budget cost.
    """
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    available = service.get_available_actions(record)
    return [
        AgentActionSchema(
            action_type=a.get("action_type", ""),
            description=a.get("description", ""),
            parameters_schema=a.get("parameters_schema", {}),
            preconditions=a.get("preconditions", []),
            time_cost=a.get("time_cost", 10),
            budget_cost=a.get("budget_cost"),
        )
        for a in available
    ]


@router.post("/{session_id}/actions", response_model=AgentActionResult)
def execute_agent_action(
    session_id: uuid.UUID,
    body: ExecuteActionRequest,
    db: SASession = Depends(get_db),  # noqa: B008
) -> AgentActionResult:
    """Execute an action and return structured result with full post-action state.

    On success returns the event details and the complete agent state.
    On failure returns success=False with an error message.
    """
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        event_record, updated_session = service.execute_action(
            record, body.action_type, body.params
        )
    except PreconditionError as exc:
        return AgentActionResult(
            success=False,
            action_type=body.action_type,
            error=str(exc),
        )
    except InvalidActionError as exc:
        return AgentActionResult(
            success=False,
            action_type=body.action_type,
            error=str(exc),
        )

    effects = (
        event_record.payload.get("effects", []) if isinstance(event_record.payload, dict) else []
    )

    new_state = _build_agent_state(service, session_id, updated_session)

    return AgentActionResult(
        success=True,
        event_id=str(event_record.id),
        sequence=event_record.sequence,
        event_type=event_record.event_type,
        action_type=body.action_type,
        new_state=new_state,
        effects=effects,
    )
