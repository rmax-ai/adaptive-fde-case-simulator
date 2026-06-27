from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ── Enums ───────────────────────────────────────────────────────────────────────


class CaseStatus(StrEnum):
    draft = "draft"
    validated = "validated"
    published = "published"
    retired = "retired"


class DifficultyLevel(StrEnum):
    introductory = "introductory"
    intermediate = "intermediate"
    advanced = "advanced"


class EvidenceType(StrEnum):
    document = "document"
    log = "log"
    table = "table"
    diagram = "diagram"
    message = "message"
    metric = "metric"
    code = "code"


class Severity(StrEnum):
    critical = "critical"
    major = "major"
    minor = "minor"


# ── Config Models ───────────────────────────────────────────────────────────────


class CaseMetadata(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    case_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", min_length=1)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    title: str
    domain: str
    status: CaseStatus
    difficulty: DifficultyLevel
    author_ids: list[str] = Field(default_factory=list)
    reviewer_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_lineage: str | None = None
    contamination_risk: str | None = None

    @field_validator("case_id")
    @classmethod
    def _check_case_id(cls, v: str) -> str:
        if not v:
            raise ValueError("case_id must not be empty")
        return v

    @field_validator("version")
    @classmethod
    def _check_semver(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("version must be a valid semver string (e.g. 1.0.0)")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"version segment '{part}' is not a number")
        return v

    @field_validator("status")
    @classmethod
    def _check_status(cls, v: CaseStatus) -> CaseStatus:
        allowed = {CaseStatus.draft, CaseStatus.validated, CaseStatus.published, CaseStatus.retired}
        if v not in allowed:
            raise ValueError(f"status must be one of {[s.value for s in allowed]}")
        return v


class BusinessState(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    stated_goal: str
    latent_goal: str | None = None
    baseline_metrics: dict[str, float | str] = Field(default_factory=dict)
    success_criteria: list[str] = Field(default_factory=list)
    budget: dict[str, Any] = Field(default_factory=dict)  # {amount: float, currency: str}
    deadline_days: int | None = None
    current_process: str | None = None
    business_risks: list[str] = Field(default_factory=list)


class SystemInfo(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    name: str
    type: str
    description: str | None = None
    constraints: list[str] = Field(default_factory=list)


class DataSource(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    name: str
    type: str
    format: str | None = None
    schema_info: str | dict[str, Any] | None = None
    refresh_frequency: str | None = None


class TechnicalState(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    systems: list[SystemInfo] = Field(default_factory=list)
    data_sources: list[DataSource] = Field(default_factory=list)
    apis: list[dict[str, Any]] = Field(default_factory=list)
    identity_model: dict[str, Any] = Field(default_factory=dict)
    deployment_environment: dict[str, Any] = Field(default_factory=dict)
    observability: dict[str, Any] = Field(default_factory=dict)
    hidden_defects: list[str] = Field(default_factory=list)
    technical_constraints: list[str] = Field(default_factory=list)


class StakeholderConfig(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    stakeholder_id: str
    role: str
    authority: int = Field(default=0, ge=0, le=10)
    trust_initial: int = Field(default=5, ge=0, le=10)
    goals: list[str] = Field(default_factory=list)
    hidden_incentives: list[str] = Field(default_factory=list)
    knowledge: list[str] = Field(default_factory=list)
    false_beliefs: list[str] = Field(default_factory=list)
    disclosure_rules: list[str] = Field(default_factory=list)
    escalation_rules: list[str] = Field(default_factory=list)
    relationships: dict[str, Any] = Field(default_factory=dict)


class OrganizationalState(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    stakeholders: list[StakeholderConfig] = Field(default_factory=list)


class GovernanceState(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    data_classification: str | None = None
    applicable_policies: list[str] = Field(default_factory=list)
    approval_rules: list[str] = Field(default_factory=list)
    human_review_boundaries: list[str] = Field(default_factory=list)
    audit_requirements: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    score_caps: dict[str, Any] = Field(default_factory=dict)
    automatic_failures: list[str] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    day: int = Field(..., ge=0)
    event_type: str
    description: str | None = None
    triggers: list[str] = Field(default_factory=list)


class TimelineConfig(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    start_day: int = Field(default=0, ge=0)
    scheduled_events: list[TimelineEvent] = Field(default_factory=list)
    conditional_events: list[TimelineEvent] = Field(default_factory=list)
    time_costs: dict[str, int] = Field(default_factory=dict)


class EvidenceArtifact(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    artifact_id: str
    type: EvidenceType
    path: str
    visible_initially: bool = False
    reveal_conditions: list[str] = Field(default_factory=list)
    classification: str | None = None
    content_version: str | None = None


class EvidenceManifest(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    artifacts: list[EvidenceArtifact] = Field(default_factory=list)


class ActionDefinition(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    action_type: str
    parameter_schema: dict[str, Any] = Field(default_factory=dict)
    preconditions: list[str] = Field(default_factory=list)
    time_cost: int | None = None
    budget_cost: float | None = None
    effects: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)


class ActionRegistry(BaseModel):
    """Domain model for case definition schema — not the simulation engine ActionRegistry."""

    model_config = {"extra": "forbid", "frozen": True}

    allowed: list[ActionDefinition] = Field(default_factory=list)


class EvaluationDimension(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    name: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    criteria: list[str] = Field(default_factory=list)
    automated_indicators: list[str] = Field(default_factory=list)
    rubric_indicators: list[str] = Field(default_factory=list)


class HardConstraint(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    constraint_type: str
    severity: str = "major"
    description: str | None = None
    condition: str


class EvaluationConfig(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    dimensions: list[EvaluationDimension] = Field(default_factory=list)
    hard_constraints: list[HardConstraint] = Field(default_factory=list)
    target_facts: list[str] = Field(default_factory=list)
    valid_strategy_patterns: list[str] = Field(default_factory=list)
    invalid_strategy_patterns: list[str] = Field(default_factory=list)
    counterfactual_notes: list[str] = Field(default_factory=list)


class CaseDefinition(BaseModel):
    """Top-level case definition model."""

    model_config = {"extra": "forbid", "frozen": True}

    metadata: CaseMetadata
    business: BusinessState
    technical: TechnicalState
    organization: OrganizationalState
    governance: GovernanceState
    timeline: TimelineConfig
    evidence: EvidenceManifest
    actions: ActionRegistry
    evaluation: EvaluationConfig
