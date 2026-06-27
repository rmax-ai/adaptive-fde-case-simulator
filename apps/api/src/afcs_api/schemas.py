"""Pydantic v2 request/response schemas for the AFCS API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Request Models ───────────────────────────────────────────────────────


class CreateSessionRequest(BaseModel):
    """Request to create a new simulation session."""

    case_id: str = Field(..., description="Case identifier (e.g. 'wrong_use_case')")
    participant_id: str | None = Field(None, description="Optional participant identifier")


class ExecuteActionRequest(BaseModel):
    """Request to execute an action in a session."""

    action_type: str = Field(..., description="Action type to execute")
    params: dict = Field(
        default_factory=dict, description="Action parameters per the action schema"
    )


class SubmitFinalRecommendationRequest(BaseModel):
    """Request to submit the final recommendation."""

    summary: str = Field(..., description="Executive summary of findings")
    recommendation: str = Field(..., description="The final recommendation")
    justification: str = Field(default="", description="Justification for recommendation")
    next_steps: list[str] = Field(default_factory=list, description="Recommended next steps")


# ── Response Models ──────────────────────────────────────────────────────


class SessionResponse(BaseModel):
    """Response containing session details with visible state."""

    model_config = {"from_attributes": True}

    id: UUID
    case_id: str
    case_version: str
    participant_id: str | None = None
    status: str
    current_sequence: int
    visible_state: dict = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime | None = None


class ExecuteActionResponse(BaseModel):
    """Response after executing an action."""

    event_id: UUID
    sequence: int
    event_type: str
    new_state: dict = Field(default_factory=dict)
    effects: list[dict] = Field(default_factory=list)


class EventResponse(BaseModel):
    """A single event in the session event stream."""

    model_config = {"from_attributes": True}

    id: UUID
    session_id: UUID
    sequence: int
    event_type: str
    actor_type: str
    actor_id: str | None = None
    payload: dict = Field(default_factory=dict)
    pre_state_hash: str = ""
    post_state_hash: str = ""
    created_at: datetime


class ArtifactResponse(BaseModel):
    """An artifact visible to the participant."""

    id: str
    type: str
    name: str
    metadata: dict = Field(default_factory=dict)


class ActionSchemaResponse(BaseModel):
    """Schema for a single available action."""

    action_type: str
    description: str
    parameters_schema: dict = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    time_cost: int = 10
    budget_cost: float | None = None


class AvailableActionsResponse(BaseModel):
    """List of available actions with their schemas."""

    actions: list[ActionSchemaResponse] = Field(default_factory=list)


class PaginatedEventsResponse(BaseModel):
    """Paginated event list response."""

    items: list[EventResponse] = Field(default_factory=list)
    total: int = 0
    from_sequence: int = 0
    limit: int = 50


class ArtifactListResponse(BaseModel):
    """List of visible artifacts."""

    artifacts: list[ArtifactResponse] = Field(default_factory=list)


# ── Stakeholder Models ────────────────────────────────────────────────────


class StakeholderInfo(BaseModel):
    """A stakeholder with role and qualitative trust signal."""

    id: str
    role: str
    trust_signal: str = Field(
        default="cooperative",
        description="Qualitative trust signal: cooperative|hesitant"
        "|blocked|escalating|awaiting_evidence",
    )


class StakeholderMessageRequest(BaseModel):
    """Request to send a message to a stakeholder."""

    message: str = Field(..., description="The message text to send")


class StakeholderMessageResponse(BaseModel):
    """Response from a stakeholder after sending a message."""

    stakeholder_id: str
    message: str
    tone: str = Field(default="neutral", description="Emotional tone of the response")
    disclosed_fact_ids: list[str] = Field(default_factory=list)


class StakeholderListResponse(BaseModel):
    """List of stakeholders in the session."""

    stakeholders: list[StakeholderInfo] = Field(default_factory=list)
