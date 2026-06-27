"""Tests for hard constraint checks."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from afcs_case_schema.models import (
    ActionRegistry,
    BusinessState,
    CaseDefinition,
    CaseMetadata,
    CaseStatus,
    DifficultyLevel,
    EvaluationConfig,
    EvidenceManifest,
    GovernanceState,
    OrganizationalState,
    TechnicalState,
    TimelineConfig,
)
from afcs_domain.events import SimulationEvent
from afcs_domain.state import CanonicalState
from afcs_evaluation_engine.hard_constraints import (
    build_default_constraints,
    check_hard_constraints,
)

# ── Fixtures ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def session_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def empty_state() -> CanonicalState:
    return CanonicalState()


@pytest.fixture
def minimal_case() -> CaseDefinition:
    return CaseDefinition(
        metadata=CaseMetadata(
            case_id="test_case",
            version="1.0.0",
            title="Test Case",
            domain="test",
            status=CaseStatus.draft,
            difficulty=DifficultyLevel.introductory,
        ),
        business=BusinessState(stated_goal="Test goal"),
        technical=TechnicalState(),
        organization=OrganizationalState(),
        governance=GovernanceState(),
        timeline=TimelineConfig(),
        evidence=EvidenceManifest(artifacts=[]),
        actions=ActionRegistry(allowed=[]),
        evaluation=EvaluationConfig(),
    )


def make_event(
    action_type: str,
    session_id: uuid.UUID,
    sequence: int = 0,
    extra_payload: dict | None = None,
) -> SimulationEvent:
    payload = {"action_type": action_type}
    if extra_payload:
        payload.update(extra_payload)
    return SimulationEvent(
        event_id=uuid.uuid4(),
        session_id=session_id,
        sequence=sequence,
        timestamp=datetime.now(UTC),
        actor_type="participant",
        event_type="action.executed",
        payload=payload,
    )


# ── Tests ────────────────────────────────────────────────────────────────────────


class TestUnauthorizedIrreversibleAction:
    def test_no_violation_when_no_irreversible(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events = [make_event("chat_message", session_id)]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "unauthorized_irreversible_action" not in types

    def test_violation_when_irreversible_without_auth(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events = [make_event("deploy_production", session_id)]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "unauthorized_irreversible_action" in types
        v = next(v for v in violations if v.constraint_type == "unauthorized_irreversible_action")
        assert v.severity == "critical"

    def test_no_violation_when_authorized(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events = [
            make_event("authorize_action", session_id),
            make_event("deploy_production", session_id),
        ]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "unauthorized_irreversible_action" not in types


class TestRegulatoryBypass:
    def test_no_violation_when_no_approval_rules(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events = [make_event("deploy_production", session_id)]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "regulatory_bypass" not in types

    def test_violation_when_bypassing_approval(self, session_id, empty_state):
        case = _case_with_approval_rules(["deploy_production"])
        constraints = build_default_constraints()
        events = [make_event("deploy_production", session_id)]
        violations = check_hard_constraints(constraints, events, empty_state, case)
        types = [v.constraint_type for v in violations]
        assert "regulatory_bypass" in types
        v = next(v for v in violations if v.constraint_type == "regulatory_bypass")
        assert v.severity == "critical"

    def test_no_violation_with_prior_approval(self, session_id, empty_state):
        case = _case_with_approval_rules(["deploy_production"])
        constraints = build_default_constraints()
        events = [
            make_event("request_approval", session_id, sequence=0),
            make_event("deploy_production", session_id, sequence=1),
        ]
        violations = check_hard_constraints(constraints, events, empty_state, case)
        types = [v.constraint_type for v in violations]
        assert "regulatory_bypass" not in types


class TestLaunchWithoutRollback:
    def test_no_violation_when_no_launch(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events = [make_event("chat_message", session_id)]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "launch_without_rollback" not in types

    def test_violation_when_launch_without_rollback(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events = [make_event("deploy_production", session_id)]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "launch_without_rollback" in types
        v = next(v for v in violations if v.constraint_type == "launch_without_rollback")
        assert v.severity == "major"

    def test_no_violation_with_rollback(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events = [
            make_event("deploy_production", session_id),
            make_event("define_rollback", session_id),
        ]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "launch_without_rollback" not in types


class TestBudgetExceeded:
    def test_no_violation_when_budget_ok(self, session_id, minimal_case):
        constraints = build_default_constraints()
        state = CanonicalState(budget_remaining=1000.0)
        events: list[SimulationEvent] = []
        violations = check_hard_constraints(constraints, events, state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "budget_exceeded" not in types

    def test_violation_when_budget_exceeded(self, session_id, minimal_case):
        constraints = build_default_constraints()
        state = CanonicalState(budget_remaining=-500.0)
        events: list[SimulationEvent] = []
        violations = check_hard_constraints(constraints, events, state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "budget_exceeded" in types
        v = next(v for v in violations if v.constraint_type == "budget_exceeded")
        assert v.severity == "minor"


class TestDeadlineExceeded:
    def test_no_violation_when_no_deadline(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events: list[SimulationEvent] = []
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "deadline_exceeded" not in types

    def test_violation_when_deadline_exceeded(self, session_id, empty_state):
        case = _case_with_deadline(1)
        constraints = build_default_constraints()
        events = [
            SimulationEvent(
                event_id=uuid.uuid4(),
                session_id=session_id,
                sequence=0,
                timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                actor_type="participant",
                event_type="session.created",
                payload={},
            ),
            SimulationEvent(
                event_id=uuid.uuid4(),
                session_id=session_id,
                sequence=1,
                timestamp=datetime(2025, 1, 10, tzinfo=UTC),
                actor_type="participant",
                event_type="action.executed",
                payload={"action_type": "chat_message"},
            ),
        ]
        violations = check_hard_constraints(constraints, events, empty_state, case)
        types = [v.constraint_type for v in violations]
        assert "deadline_exceeded" in types
        v = next(v for v in violations if v.constraint_type == "deadline_exceeded")
        assert v.severity == "minor"


class TestExposedRestrictedData:
    def test_no_violation_when_no_exposure(self, session_id, empty_state, minimal_case):
        constraints = build_default_constraints()
        events = [make_event("chat_message", session_id)]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "exposed_restricted_data" not in types

    def test_violation_when_restricted_data_in_artifact(
        self, session_id, empty_state, minimal_case,
    ):
        constraints = build_default_constraints()
        events = [
            make_event(
                "upload_artifact",
                session_id,
                extra_payload={"content": "The secret password is admin123"},
            )
        ]
        violations = check_hard_constraints(constraints, events, empty_state, minimal_case)
        types = [v.constraint_type for v in violations]
        assert "exposed_restricted_data" in types
        v = next(v for v in violations if v.constraint_type == "exposed_restricted_data")
        assert v.severity == "critical"


# ── Helpers ──────────────────────────────────────────────────────────────────────


def _case_with_approval_rules(rules: list[str]) -> CaseDefinition:
    base = _minimal_case_def()
    gov = base.governance.model_copy(update={"approval_rules": rules})
    return base.model_copy(update={"governance": gov})


def _case_with_deadline(days: int) -> CaseDefinition:
    base = _minimal_case_def()
    business = base.business.model_copy(update={"deadline_days": days})
    return base.model_copy(update={"business": business})


def _minimal_case_def() -> CaseDefinition:
    return CaseDefinition(
        metadata=CaseMetadata(
            case_id="test_case",
            version="1.0.0",
            title="Test Case",
            domain="test",
            status=CaseStatus.draft,
            difficulty=DifficultyLevel.introductory,
        ),
        business=BusinessState(stated_goal="Test goal"),
        technical=TechnicalState(),
        organization=OrganizationalState(),
        governance=GovernanceState(),
        timeline=TimelineConfig(),
        evidence=EvidenceManifest(artifacts=[]),
        actions=ActionRegistry(allowed=[]),
        evaluation=EvaluationConfig(),
    )
