from __future__ import annotations

from collections.abc import Callable

from afcs_case_schema.models import CaseDefinition
from afcs_domain.events import SimulationEvent
from afcs_domain.state import CanonicalState
from pydantic import BaseModel, Field


class ValidatorResult(BaseModel):
    """Result produced by a single validator check."""

    validator_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    evidence_event_ids: list[str] = Field(default_factory=list)
    details: str = ""


# ── Validator type alias ────────────────────────────────────────────────────────

ValidatorFn = Callable[[list[SimulationEvent], CanonicalState, CaseDefinition], ValidatorResult]


# ── Helpers ──────────────────────────────────────────────────────────────────────


def _events_of_type(events: list[SimulationEvent], action_type: str) -> list[SimulationEvent]:
    """Return events whose payload.action_type matches *action_type*."""
    return [e for e in events if e.payload.get("action_type") == action_type]


def _any_event_of_type(events: list[SimulationEvent], action_type: str) -> bool:
    """True if at least one event has the given action_type in its payload."""
    return any(e.payload.get("action_type") == action_type for e in events)


def _count_events_of_type(events: list[SimulationEvent], action_type: str) -> int:
    return sum(1 for e in events if e.payload.get("action_type") == action_type)


# ── Individual Validators ────────────────────────────────────────────────────────


def baseline_defined(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that a 'define_baseline' action was executed."""
    passed = _any_event_of_type(events, "define_baseline")
    ids = [e.event_id for e in events if e.payload.get("action_type") == "define_baseline"]
    return ValidatorResult(
        validator_name="baseline_defined",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in ids],
        details="Baseline was defined." if passed else "No baseline definition found.",
    )


def success_criteria_defined(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that a 'define_success_metric' action was executed."""
    passed = _any_event_of_type(events, "define_success_metric")
    ids = [e.event_id for e in events if e.payload.get("action_type") == "define_success_metric"]
    return ValidatorResult(
        validator_name="success_criteria_defined",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in ids],
        details="Success criteria were defined."
        if passed
        else "No success criteria definition found.",
    )


def decisive_evidence_inspected(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that at least N 'inspect_artifact' actions were performed, where N is
    derived from the case definition's evidence manifest."""
    min_required = max(1, len(case_definition.evidence.artifacts) // 2)
    count = _count_events_of_type(events, "inspect_artifact")
    passed = count >= min_required
    ids = [e.event_id for e in events if e.payload.get("action_type") == "inspect_artifact"]
    return ValidatorResult(
        validator_name="decisive_evidence_inspected",
        passed=passed,
        score=min(1.0, count / min_required) if min_required > 0 else 1.0,
        evidence_event_ids=[str(i) for i in ids],
        details=f"Inspected {count}/{min_required} required artifacts."
        if passed
        else f"Only inspected {count} artifacts; need at least {min_required}.",
    )


def required_approval_obtained(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that a 'request_approval' action was executed."""
    passed = _any_event_of_type(events, "request_approval")
    ids = [e.event_id for e in events if e.payload.get("action_type") == "request_approval"]
    return ValidatorResult(
        validator_name="required_approval_obtained",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in ids],
        details="Required approval was obtained." if passed else "No approval request found.",
    )


def irreversible_action_protected(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """If any irreversible actions were performed, a 'define_rollback' must exist."""
    irreversible_types = {"deploy_production", "delete_data", "migrate_schema", "terminate_service"}
    has_irreversible = any(e.payload.get("action_type") in irreversible_types for e in events)
    has_rollback = _any_event_of_type(events, "define_rollback")
    passed = (not has_irreversible) or has_rollback
    irr_ids = [e.event_id for e in events if e.payload.get("action_type") in irreversible_types]
    rollback_ids = [e.event_id for e in events if e.payload.get("action_type") == "define_rollback"]
    return ValidatorResult(
        validator_name="irreversible_action_protected",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in irr_ids + rollback_ids],
        details="Irreversible actions are protected by a rollback plan."
        if passed
        else "Irreversible actions found without a rollback plan.",
    )


def rollback_defined(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that a 'define_rollback' action was executed."""
    passed = _any_event_of_type(events, "define_rollback")
    ids = [e.event_id for e in events if e.payload.get("action_type") == "define_rollback"]
    return ValidatorResult(
        validator_name="rollback_defined",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in ids],
        details="Rollback plan was defined." if passed else "No rollback plan found.",
    )


def owner_assigned(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that an 'assign_owner' action was executed."""
    passed = _any_event_of_type(events, "assign_owner")
    ids = [e.event_id for e in events if e.payload.get("action_type") == "assign_owner"]
    return ValidatorResult(
        validator_name="owner_assigned",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in ids],
        details="Owner was assigned." if passed else "No owner assignment found.",
    )


def budget_respected(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that the budget was never exceeded in events or final state."""
    budget = case_definition.business.budget
    limit: float = float(budget.get("amount", 0)) if isinstance(budget, dict) else 0.0
    remaining = final_state.budget_remaining
    passed = remaining >= 0
    overshoot_ids = [
        e.event_id
        for e in events
        if e.payload.get("budget_remaining", remaining) is not None
        and isinstance(e.payload.get("budget_remaining"), (int, float))
        and e.payload["budget_remaining"] < 0
    ]
    return ValidatorResult(
        validator_name="budget_respected",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in overshoot_ids],
        details=f"Budget respected: {remaining:.2f} remaining of {limit:.2f}."
        if passed
        else f"Budget exceeded: {remaining:.2f} remaining (overdrawn).",
    )


def deadline_respected(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that the session completed within the deadline."""
    deadline_days = case_definition.business.deadline_days
    if deadline_days is None:
        return ValidatorResult(
            validator_name="deadline_respected",
            passed=True,
            score=1.0,
            evidence_event_ids=[],
            details="No deadline defined; automatically respected.",
        )
    # Compute elapsed time from events
    if not events:
        return ValidatorResult(
            validator_name="deadline_respected",
            passed=True,
            score=1.0,
            evidence_event_ids=[],
            details="No events; deadline trivially respected.",
        )
    first_ts = events[0].timestamp
    last_ts = events[-1].timestamp
    elapsed_days = (last_ts - first_ts).total_seconds() / 86400.0
    passed = elapsed_days <= deadline_days
    return ValidatorResult(
        validator_name="deadline_respected",
        passed=passed,
        score=1.0 if passed else max(0.0, 1.0 - (elapsed_days - deadline_days) / deadline_days),
        evidence_event_ids=[str(events[0].event_id), str(events[-1].event_id)],
        details=f"Completed in {elapsed_days:.1f} days (deadline: {deadline_days} days)."
        if passed
        else f"Exceeded deadline: {elapsed_days:.1f} days (limit: {deadline_days} days).",
    )


def prohibited_action_avoided(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that no forbidden actions from the case config were executed."""
    forbidden = case_definition.governance.forbidden_actions
    if not forbidden:
        return ValidatorResult(
            validator_name="prohibited_action_avoided",
            passed=True,
            score=1.0,
            evidence_event_ids=[],
            details="No prohibited actions defined in case config.",
        )
    violations: list[str] = []
    evidence_ids: list[str] = []
    for event in events:
        action_type = event.payload.get("action_type", "")
        if action_type in forbidden:
            violations.append(action_type)
            evidence_ids.append(str(event.event_id))
    passed = len(violations) == 0
    return ValidatorResult(
        validator_name="prohibited_action_avoided",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=evidence_ids,
        details="No prohibited actions were executed."
        if passed
        else f"Prohibited actions found: {', '.join(violations)}.",
    )


def critical_risk_registered(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that a 'register_risk' action was executed."""
    passed = _any_event_of_type(events, "register_risk")
    ids = [e.event_id for e in events if e.payload.get("action_type") == "register_risk"]
    return ValidatorResult(
        validator_name="critical_risk_registered",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in ids],
        details="Critical risks were registered." if passed else "No risk registration found.",
    )


def evaluation_includes_failure_cases(
    events: list[SimulationEvent],
    final_state: CanonicalState,
    case_definition: CaseDefinition,
) -> ValidatorResult:
    """Check that an evaluation was defined with failure classes."""
    passed = _any_event_of_type(events, "define_evaluation_with_failures")
    ids = [
        e.event_id
        for e in events
        if e.payload.get("action_type") == "define_evaluation_with_failures"
    ]
    return ValidatorResult(
        validator_name="evaluation_includes_failure_cases",
        passed=passed,
        score=1.0 if passed else 0.0,
        evidence_event_ids=[str(i) for i in ids],
        details="Evaluation includes failure cases."
        if passed
        else "No evaluation with failure cases defined.",
    )


# ── Registry builder ─────────────────────────────────────────────────────────────


def build_default_validators() -> dict[str, ValidatorFn]:
    """Return a dict mapping validator names to their callable implementations."""
    return {
        "baseline_defined": baseline_defined,
        "success_criteria_defined": success_criteria_defined,
        "decisive_evidence_inspected": decisive_evidence_inspected,
        "required_approval_obtained": required_approval_obtained,
        "irreversible_action_protected": irreversible_action_protected,
        "rollback_defined": rollback_defined,
        "owner_assigned": owner_assigned,
        "budget_respected": budget_respected,
        "deadline_respected": deadline_respected,
        "prohibited_action_avoided": prohibited_action_avoided,
        "critical_risk_registered": critical_risk_registered,
        "evaluation_includes_failure_cases": evaluation_includes_failure_cases,
    }
