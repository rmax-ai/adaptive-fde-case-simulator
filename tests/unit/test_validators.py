"""Tests for all 12 automated validators."""

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
    EvidenceArtifact,
    EvidenceManifest,
    EvidenceType,
    GovernanceState,
    OrganizationalState,
    TechnicalState,
    TimelineConfig,
)
from afcs_domain.events import SimulationEvent
from afcs_domain.state import CanonicalState
from afcs_evaluation_engine.validators import (
    baseline_defined,
    budget_respected,
    critical_risk_registered,
    deadline_respected,
    decisive_evidence_inspected,
    evaluation_includes_failure_cases,
    irreversible_action_protected,
    owner_assigned,
    prohibited_action_avoided,
    required_approval_obtained,
    rollback_defined,
    success_criteria_defined,
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


class TestBaselineDefined:
    def test_passes_when_baseline_defined(self, session_id, empty_state, minimal_case):
        events = [make_event("define_baseline", session_id)]
        result = baseline_defined(events, empty_state, minimal_case)
        assert result.passed is True
        assert result.score == 1.0
        assert result.validator_name == "baseline_defined"

    def test_fails_when_no_baseline(self, session_id, empty_state, minimal_case):
        events = [make_event("chat_message", session_id)]
        result = baseline_defined(events, empty_state, minimal_case)
        assert result.passed is False
        assert result.score == 0.0


class TestSuccessCriteriaDefined:
    def test_passes_when_criteria_defined(self, session_id, empty_state, minimal_case):
        events = [make_event("define_success_metric", session_id)]
        result = success_criteria_defined(events, empty_state, minimal_case)
        assert result.passed is True
        assert result.score == 1.0

    def test_fails_when_no_criteria(self, session_id, empty_state, minimal_case):
        events: list[SimulationEvent] = []
        result = success_criteria_defined(events, empty_state, minimal_case)
        assert result.passed is False
        assert result.score == 0.0


class TestDecisiveEvidenceInspected:
    def test_passes_with_sufficient_inspections(self, session_id, empty_state):
        case = _case_with_n_artifacts(4)
        events = [make_event("inspect_artifact", session_id) for _ in range(3)]
        result = decisive_evidence_inspected(events, empty_state, case)
        assert result.passed is True

    def test_fails_with_insufficient_inspections(self, session_id, empty_state):
        case = _case_with_n_artifacts(10)
        events = [make_event("inspect_artifact", session_id) for _ in range(2)]
        result = decisive_evidence_inspected(events, empty_state, case)
        assert result.passed is False
        assert result.score < 1.0


class TestRequiredApprovalObtained:
    def test_passes_when_approval_requested(self, session_id, empty_state, minimal_case):
        events = [make_event("request_approval", session_id)]
        result = required_approval_obtained(events, empty_state, minimal_case)
        assert result.passed is True

    def test_fails_when_no_approval(self, session_id, empty_state, minimal_case):
        events: list[SimulationEvent] = []
        result = required_approval_obtained(events, empty_state, minimal_case)
        assert result.passed is False


class TestIrreversibleActionProtected:
    def test_passes_when_no_irreversible_actions(self, session_id, empty_state, minimal_case):
        events = [make_event("chat_message", session_id)]
        result = irreversible_action_protected(events, empty_state, minimal_case)
        assert result.passed is True

    def test_passes_with_rollback_for_irreversible(self, session_id, empty_state, minimal_case):
        events = [
            make_event("deploy_production", session_id),
            make_event("define_rollback", session_id),
        ]
        result = irreversible_action_protected(events, empty_state, minimal_case)
        assert result.passed is True

    def test_fails_without_rollback(self, session_id, empty_state, minimal_case):
        events = [make_event("deploy_production", session_id)]
        result = irreversible_action_protected(events, empty_state, minimal_case)
        assert result.passed is False


class TestRollbackDefined:
    def test_passes_when_rollback_defined(self, session_id, empty_state, minimal_case):
        events = [make_event("define_rollback", session_id)]
        result = rollback_defined(events, empty_state, minimal_case)
        assert result.passed is True

    def test_fails_when_no_rollback(self, session_id, empty_state, minimal_case):
        events: list[SimulationEvent] = []
        result = rollback_defined(events, empty_state, minimal_case)
        assert result.passed is False


class TestOwnerAssigned:
    def test_passes_when_owner_assigned(self, session_id, empty_state, minimal_case):
        events = [make_event("assign_owner", session_id)]
        result = owner_assigned(events, empty_state, minimal_case)
        assert result.passed is True

    def test_fails_when_no_owner(self, session_id, empty_state, minimal_case):
        events: list[SimulationEvent] = []
        result = owner_assigned(events, empty_state, minimal_case)
        assert result.passed is False


class TestBudgetRespected:
    def test_passes_when_budget_not_exceeded(self, session_id, minimal_case):
        state = CanonicalState(budget_remaining=1000.0)
        events: list[SimulationEvent] = []
        result = budget_respected(events, state, minimal_case)
        assert result.passed is True

    def test_fails_when_budget_exceeded(self, session_id, minimal_case):
        state = CanonicalState(budget_remaining=-500.0)
        events: list[SimulationEvent] = []
        result = budget_respected(events, state, minimal_case)
        assert result.passed is False


class TestDeadlineRespected:
    def test_passes_when_no_deadline(self, session_id, empty_state, minimal_case):
        events: list[SimulationEvent] = []
        result = deadline_respected(events, empty_state, minimal_case)
        assert result.passed is True

    def test_passes_when_within_deadline(self, session_id, empty_state):
        case = _case_with_deadline(10)
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
                timestamp=datetime(2025, 1, 5, tzinfo=UTC),
                actor_type="participant",
                event_type="action.executed",
                payload={"action_type": "chat_message"},
            ),
        ]
        result = deadline_respected(events, empty_state, case)
        assert result.passed is True

    def test_fails_when_deadline_exceeded(self, session_id, empty_state):
        case = _case_with_deadline(2)
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
        result = deadline_respected(events, empty_state, case)
        assert result.passed is False


class TestProhibitedActionAvoided:
    def test_passes_when_no_prohibited_actions(self, session_id, empty_state):
        case = _case_with_forbidden_actions(["delete_all_data"])
        events = [make_event("chat_message", session_id)]
        result = prohibited_action_avoided(events, empty_state, case)
        assert result.passed is True

    def test_fails_when_prohibited_action_executed(self, session_id, empty_state):
        case = _case_with_forbidden_actions(["delete_all_data"])
        events = [make_event("delete_all_data", session_id)]
        result = prohibited_action_avoided(events, empty_state, case)
        assert result.passed is False

    def test_passes_when_no_forbidden_defined(self, session_id, empty_state, minimal_case):
        events = [make_event("delete_all_data", session_id)]
        result = prohibited_action_avoided(events, empty_state, minimal_case)
        assert result.passed is True


class TestCriticalRiskRegistered:
    def test_passes_when_risk_registered(self, session_id, empty_state, minimal_case):
        events = [make_event("register_risk", session_id)]
        result = critical_risk_registered(events, empty_state, minimal_case)
        assert result.passed is True

    def test_fails_when_no_risk(self, session_id, empty_state, minimal_case):
        events: list[SimulationEvent] = []
        result = critical_risk_registered(events, empty_state, minimal_case)
        assert result.passed is False


class TestEvaluationIncludesFailureCases:
    def test_passes_when_evaluation_with_failures(self, session_id, empty_state, minimal_case):
        events = [make_event("define_evaluation_with_failures", session_id)]
        result = evaluation_includes_failure_cases(events, empty_state, minimal_case)
        assert result.passed is True

    def test_fails_when_no_evaluation(self, session_id, empty_state, minimal_case):
        events = [make_event("define_baseline", session_id)]
        result = evaluation_includes_failure_cases(events, empty_state, minimal_case)
        assert result.passed is False


# ── Helpers ──────────────────────────────────────────────────────────────────────


def _case_with_n_artifacts(n: int) -> CaseDefinition:
    artifacts = [
        EvidenceArtifact(
            artifact_id=f"art_{i}",
            type=EvidenceType.document,
            path=f"/docs/file_{i}.md",
        )
        for i in range(n)
    ]
    base = _minimal_case_def()
    return base.model_copy(update={"evidence": EvidenceManifest(artifacts=artifacts)})


def _case_with_deadline(days: int) -> CaseDefinition:
    base = _minimal_case_def()
    business = base.business.model_copy(update={"deadline_days": days})
    return base.model_copy(update={"business": business})


def _case_with_forbidden_actions(actions: list[str]) -> CaseDefinition:
    base = _minimal_case_def()
    gov = base.governance.model_copy(update={"forbidden_actions": actions})
    return base.model_copy(update={"governance": gov})


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
