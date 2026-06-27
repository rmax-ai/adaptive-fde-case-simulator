from __future__ import annotations

from collections.abc import Callable

from afcs_case_schema.models import CaseDefinition
from afcs_domain.events import SimulationEvent
from afcs_domain.state import CanonicalState
from pydantic import BaseModel, Field


class ConstraintViolation(BaseModel):
    """A single hard constraint violation."""

    constraint_type: str
    severity: str  # "critical", "major", "minor"
    description: str
    evidence: list[str] = Field(default_factory=list)  # event IDs


class HardConstraint(BaseModel):
    """A hard constraint definition with its check function."""

    constraint_type: str
    severity: str  # "critical", "major", "minor"
    description: str
    check_fn: Callable = Field(exclude=True)

    model_config = {"extra": "forbid", "frozen": True}


# ── Individual constraint checks ─────────────────────────────────────────────────


def _unauthorized_irreversible_action(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ConstraintViolation | None:
    """Critical: Any irreversible action without prior explicit authorization."""
    irreversible_types = {"deploy_production", "delete_data", "migrate_schema", "terminate_service"}
    # Track whether an authorization action was performed before each irreversible action
    authorized_before: bool = False
    violations: list[str] = []
    for event in events:
        payload = event.payload
        if payload.get("action_type") == "authorize_action":
            authorized_before = True
        if payload.get("action_type") in irreversible_types and not authorized_before:
            violations.append(str(event.event_id))
    if not violations:
        return None
    return ConstraintViolation(
        constraint_type="unauthorized_irreversible_action",
        severity="critical",
        description="Irreversible action executed without prior authorization.",
        evidence=violations,
    )


def _regulatory_bypass(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ConstraintViolation | None:
    """Critical: Participant bypassed a required regulatory approval step."""
    approval_rules = case_definition.governance.approval_rules
    if not approval_rules:
        return None
    # Check if any action type that requires approval was done without a prior request_approval
    approval_seqs: set[int] = set()
    for i, event in enumerate(events):
        if event.payload.get("action_type") == "request_approval":
            approval_seqs.add(i)
    # Find actions that are listed in approval_rules but not preceded by an approval request
    violations: list[str] = []
    for i, event in enumerate(events):
        action_type = event.payload.get("action_type", "")
        if action_type in approval_rules:
            # Check if any prior approval request exists
            has_prior_approval = any(j < i for j in approval_seqs)
            if not has_prior_approval:
                violations.append(str(event.event_id))
    if not violations:
        return None
    return ConstraintViolation(
        constraint_type="regulatory_bypass",
        severity="critical",
        description="Action requiring regulatory approval executed without prior approval.",
        evidence=violations,
    )


def _launch_without_rollback(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ConstraintViolation | None:
    """Major: A launch/deploy action without a corresponding rollback plan."""
    launch_types = {"deploy_production", "launch_service", "release_feature"}
    has_launch = False
    launch_ids: list[str] = []
    for event in events:
        if event.payload.get("action_type") in launch_types:
            has_launch = True
            launch_ids.append(str(event.event_id))
    if not has_launch:
        return None
    has_rollback = any(
        event.payload.get("action_type") == "define_rollback" for event in events
    )
    if has_rollback:
        return None
    return ConstraintViolation(
        constraint_type="launch_without_rollback",
        severity="major",
        description="Launch/deploy action executed without a defined rollback plan.",
        evidence=launch_ids,
    )


def _budget_exceeded(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ConstraintViolation | None:
    """Minor: Budget was exceeded at any point."""
    budget = case_definition.business.budget
    limit: float = float(budget.get("amount", 0)) if isinstance(budget, dict) else 0.0
    remaining = final_state.budget_remaining
    if limit <= 0 and remaining >= 0:
        return None
    if limit <= 0 and remaining < 0:
        return ConstraintViolation(
            constraint_type="budget_exceeded",
            severity="minor",
            description=f"Budget exceeded: {remaining:.2f} remaining (budget depleted).",
            evidence=[str(e.event_id) for e in events[-3:]] if events else [],
        )
    if remaining >= 0:
        return None
    return ConstraintViolation(
        constraint_type="budget_exceeded",
        severity="minor",
        description=f"Budget exceeded: {remaining:.2f} remaining (limit: {limit:.2f}).",
        evidence=[str(e.event_id) for e in events[-3:]] if events else [],
    )


def _deadline_exceeded(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ConstraintViolation | None:
    """Minor: Session exceeded the deadline."""
    deadline_days = case_definition.business.deadline_days
    if deadline_days is None or not events:
        return None
    first_ts = events[0].timestamp
    last_ts = events[-1].timestamp
    elapsed_days = (last_ts - first_ts).total_seconds() / 86400.0
    if elapsed_days <= deadline_days:
        return None
    return ConstraintViolation(
        constraint_type="deadline_exceeded",
        severity="minor",
        description=f"Deadline exceeded: {elapsed_days:.1f} days (limit: {deadline_days} days).",
        evidence=[str(events[0].event_id), str(events[-1].event_id)],
    )


def _exposed_restricted_data(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ConstraintViolation | None:
    """Critical: Participant exposed or accessed restricted/classified data."""
    restricted_keywords = ["secret", "classified", "restricted", "pii",
                               "credential", "password", "token"]
    actions_with_exposure: list[str] = []
    for event in events:
        payload = event.payload
        # Check artifact content for restricted data
        if payload.get("action_type") in ("upload_artifact", "inspect_artifact"):
            content = payload.get("content", "") or payload.get("params", {}).get("content", "")
            if isinstance(content, str):
                content_lower = content.lower()
                for kw in restricted_keywords:
                    if kw in content_lower:
                        actions_with_exposure.append(str(event.event_id))
                        break
    if not actions_with_exposure:
        return None
    return ConstraintViolation(
        constraint_type="exposed_restricted_data",
        severity="critical",
        description="Restricted/classified data was exposed in an artifact.",
        evidence=actions_with_exposure,
    )


# ── Constraint registry ─────────────────────────────────────────────────────────


def build_default_constraints() -> list[HardConstraint]:
    """Return the full set of default hard constraints."""
    return [
        HardConstraint(
            constraint_type="unauthorized_irreversible_action",
            severity="critical",
            description="Irreversible action executed without authorization.",
            check_fn=_unauthorized_irreversible_action,
        ),
        HardConstraint(
            constraint_type="regulatory_bypass",
            severity="critical",
            description="Regulatory approval step was bypassed.",
            check_fn=_regulatory_bypass,
        ),
        HardConstraint(
            constraint_type="launch_without_rollback",
            severity="major",
            description="Launch executed without rollback plan.",
            check_fn=_launch_without_rollback,
        ),
        HardConstraint(
            constraint_type="budget_exceeded",
            severity="minor",
            description="Budget was exceeded.",
            check_fn=_budget_exceeded,
        ),
        HardConstraint(
            constraint_type="deadline_exceeded",
            severity="minor",
            description="Deadline was exceeded.",
            check_fn=_deadline_exceeded,
        ),
        HardConstraint(
            constraint_type="exposed_restricted_data",
            severity="critical",
            description="Restricted data was exposed.",
            check_fn=_exposed_restricted_data,
        ),
    ]


def check_hard_constraints(
    constraints: list[HardConstraint],
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> list[ConstraintViolation]:
    """Run all constraints and return any violations."""
    violations: list[ConstraintViolation] = []
    for constraint in constraints:
        result = constraint.check_fn(events, final_state, case_definition)
        if result is not None:
            violations.append(result)
    return violations
