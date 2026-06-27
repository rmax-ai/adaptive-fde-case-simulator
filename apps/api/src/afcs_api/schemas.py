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


# ── Evaluation Models ────────────────────────────────────────────────────


class DimensionScore(BaseModel):
    """Score for a single evaluation dimension."""

    name: str
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    max_score: float = 100.0
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    findings: list[str] = Field(default_factory=list)
    missed_evidence: list[str] = Field(default_factory=list)


class HardConstraintOutcome(BaseModel):
    """Result of a single hard constraint check."""

    constraint_type: str
    severity: str = "major"
    passed: bool
    description: str | None = None
    details: str | None = None


class EvaluationResponse(BaseModel):
    """Evaluation results for a completed session."""

    session_id: str
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    dimensions: list[DimensionScore] = Field(default_factory=list)
    hard_constraint_violations: list[HardConstraintOutcome] = Field(default_factory=list)
    strongest_behaviors: list[str] = Field(default_factory=list)
    weakest_behaviors: list[str] = Field(default_factory=list)
    missed_evidence: list[str] = Field(default_factory=list)
    status: str


# ── Replay Models ──────────────────────────────────────────────────────────


class ReplayEventResponse(BaseModel):
    """A single event in the replay timeline with state diff."""

    event: dict = Field(default_factory=dict, description="Raw event data")
    state_diff: list[dict] = Field(
        default_factory=list,
        description="Computed state diffs (pre\u2192post)",
    )
    dimensions: list[str] = Field(
        default_factory=list,
        description="Relevant evaluation dimensions",
    )
    pre_state_snapshot: dict = Field(
        default_factory=dict, description="Truncated before-state"
    )
    post_state_snapshot: dict = Field(
        default_factory=dict, description="Truncated after-state"
    )
    summary: str = ""


class ReplayTimelineResponse(BaseModel):
    """Chronological replay timeline for a session."""

    session_id: str
    events: list[ReplayEventResponse] = Field(default_factory=list)
    total_events: int = 0
    available_dimensions: list[str] = Field(default_factory=list)


class ExpertReviewRequest(BaseModel):
    """Request payload for expert dimension scoring with event citations."""

    dimension_scores: list[ExpertDimensionScore] = Field(
        default_factory=list,
        description="Scores for each evaluation dimension with supporting event citations",
    )
    overall_comment: str = Field(default="", description="Overall expert commentary")


class ExpertDimensionScore(BaseModel):
    """Score for a single evaluation dimension with event citations."""

    dimension: str = Field(..., description="Dimension name (e.g. 'discovery', 'technical')")
    score: float = Field(..., ge=0.0, le=100.0, description="Expert-assigned score 0-100")
    justification: str = Field(default="", description="Narrative justification")
    cited_event_ids: list[str] = Field(
        default_factory=list,
        description="Event IDs that support this score",
    )
    cited_event_summaries: list[str] = Field(
        default_factory=list,
        description="Human-readable summaries of cited events",
    )
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class ExpertReviewResponse(BaseModel):
    """Response for an expert review submission."""

    session_id: str
    dimension_scores: list[ExpertDimensionScore] = Field(default_factory=list)
    overall_comment: str = ""
    submitted_at: str = ""


class ReportResponse(BaseModel):
    """Full participant report for a completed session."""

    session_id: str
    case_id: str
    case_version: str
    participant_id: str | None = None
    status: str
    evaluation: EvaluationResponse | None = None
    timeline: list[dict] = Field(default_factory=list)
    artifacts_inspected: list[str] = Field(default_factory=list)
    stakeholder_interactions: list[dict] = Field(default_factory=list)
    recommendation: dict = Field(default_factory=dict)


# ── Agent API Models ─────────────────────────────────────────────────────


class AgentActionSchema(BaseModel):
    """Action schema optimized for AI agent consumption with full JSON Schema specs."""

    action_type: str = Field(..., description="Unique action type identifier")
    description: str = Field(..., description="Human-readable description of the action")
    parameters_schema: dict = Field(
        default_factory=dict,
        description="Full JSON Schema object describing required and optional parameters",
    )
    preconditions: list[str] = Field(
        default_factory=list,
        description="List of unmet preconditions (empty = action is available)",
    )
    time_cost: int = Field(default=10, description="Estimated time cost in minutes")
    budget_cost: float | None = Field(default=None, description="Budget cost if any")


class AgentStateResponse(BaseModel):
    """Verbose machine-readable state for AI agent consumption."""

    session_id: str = Field(..., description="UUID of the session")
    case_id: str = Field(..., description="Case identifier")
    status: str = Field(..., description="Session status (in_progress, completed, etc.)")
    phase: str = Field(default="discovery", description="Current simulation phase")
    current_sequence: int = Field(default=0, description="Next event sequence number")
    budget_remaining: float = Field(default=0.0, description="Remaining budget in USD")
    artifacts: list[dict] = Field(default_factory=list, description="Visible artifacts")
    stakeholder_relationships: dict = Field(
        default_factory=dict,
        description="Stakeholder trust signals keyed by stakeholder ID",
    )
    flags: dict = Field(default_factory=dict, description="State flags")
    metadata: dict = Field(default_factory=dict, description="Additional state metadata")
    available_actions: list[AgentActionSchema] = Field(
        default_factory=list,
        description="Actions available in current state",
    )
    stakeholders: list[StakeholderInfo] = Field(
        default_factory=list,
        description="Stakeholders in the session",
    )
    event_count: int = Field(default=0, description="Total events in the session event stream")


class AgentActionResult(BaseModel):
    """Structured result of executing an action via the agent API."""

    success: bool = Field(default=True, description="Whether the action was executed successfully")
    event_id: str = Field(default="", description="UUID of the emitted event")
    sequence: int = Field(default=0, description="Event sequence number")
    event_type: str = Field(default="", description="Type of event emitted")
    action_type: str = Field(default="", description="The action type that was executed")
    new_state: AgentStateResponse | None = Field(
        default=None,
        description="Full agent state after action execution",
    )
    error: str | None = Field(default=None, description="Error message if action failed")
    effects: list[dict] = Field(default_factory=list, description="Side effects from the action")
