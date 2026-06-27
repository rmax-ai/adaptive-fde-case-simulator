"""Tests for report generation."""

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
from afcs_evaluation_engine.hard_constraints import ConstraintViolation
from afcs_evaluation_engine.report_service import ReportService
from afcs_evaluation_engine.scoring import DimensionScore

# ── Fixtures ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def session_id() -> str:
    return str(uuid.uuid4())


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


@pytest.fixture
def sample_dimension_scores() -> list[DimensionScore]:
    return [
        DimensionScore(
            dimension="discovery",
            machine_score=0.9,
            final_score=0.9,
            confidence=0.85,
            evidence_event_ids=["evt-1", "evt-2"],
            strengths=["baseline_defined: good", "success_criteria_defined: good"],
            failures=[],
            uncertainties=[],
        ),
        DimensionScore(
            dimension="technical",
            machine_score=0.6,
            final_score=0.6,
            confidence=0.6,
            evidence_event_ids=["evt-3"],
            strengths=["decisive_evidence_inspected: ok"],
            failures=["irreversible_action_protected: no rollback"],
            uncertainties=[],
        ),
        DimensionScore(
            dimension="delivery",
            machine_score=0.3,
            final_score=0.3,
            confidence=0.4,
            evidence_event_ids=[],
            strengths=[],
            failures=["deadline_respected: exceeded", "budget_respected: overdrawn"],
            uncertainties=["partial compliance"],
        ),
        DimensionScore(
            dimension="evaluation_quality",
            machine_score=0.75,
            final_score=0.75,
            confidence=0.7,
            evidence_event_ids=["evt-4"],
            strengths=["evaluation_includes_failure_cases: good"],
            failures=[],
            uncertainties=[],
        ),
        DimensionScore(
            dimension="governance",
            machine_score=0.5,
            final_score=0.5,
            confidence=0.5,
            evidence_event_ids=["evt-5"],
            strengths=["required_approval_obtained: ok"],
            failures=["prohibited_action_avoided: used forbidden action"],
            uncertainties=[],
        ),
        DimensionScore(
            dimension="operational_sustainability",
            machine_score=0.2,
            final_score=0.2,
            confidence=0.3,
            evidence_event_ids=[],
            strengths=[],
            failures=["rollback_defined: missing", "irreversible_action_protected: missing"],
            uncertainties=[],
        ),
    ]


@pytest.fixture
def sample_violations() -> list[ConstraintViolation]:
    return [
        ConstraintViolation(
            constraint_type="budget_exceeded",
            severity="minor",
            description="Budget was exceeded by $500",
            evidence=["evt-3"],
        ),
    ]


@pytest.fixture
def sample_events(session_id: str) -> list[SimulationEvent]:
    sid = uuid.UUID(session_id)
    return [
        SimulationEvent(
            event_id=uuid.uuid4(),
            session_id=sid,
            sequence=0,
            timestamp=datetime(2025, 1, 1, tzinfo=UTC),
            actor_type="participant",
            event_type="session.created",
            payload={},
        ),
        SimulationEvent(
            event_id=uuid.uuid4(),
            session_id=sid,
            sequence=1,
            timestamp=datetime(2025, 1, 2, tzinfo=UTC),
            actor_type="participant",
            event_type="action.executed",
            payload={"action_type": "define_baseline"},
        ),
        SimulationEvent(
            event_id=uuid.uuid4(),
            session_id=sid,
            sequence=2,
            timestamp=datetime(2025, 1, 3, tzinfo=UTC),
            actor_type="participant",
            event_type="action.executed",
            payload={"action_type": "request_approval"},
        ),
        SimulationEvent(
            event_id=uuid.uuid4(),
            session_id=sid,
            sequence=3,
            timestamp=datetime(2025, 1, 4, tzinfo=UTC),
            actor_type="participant",
            event_type="action.executed",
            payload={"action_type": "revise_assumption"},
        ),
    ]


# ── Tests ────────────────────────────────────────────────────────────────────────


class TestReportService:
    def test_generates_report_with_all_fields(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        assert report.session_id == session_id
        assert report.case_id == "test_case"
        assert 0.0 <= report.overall_score <= 1.0
        assert len(report.dimension_scores) == 6
        assert len(report.hard_constraint_outcomes) == 1
        assert report.generated_at is not None

    def test_identifies_strongest_behaviors(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        # discovery (0.9) and evaluation_quality (0.75) >= 0.7 should have strengths
        assert len(report.strongest_behaviors) >= 1

    def test_identifies_weakest_behaviors(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        # operational_sustainability (0.2) and delivery (0.3) <= 0.4
        assert len(report.weakest_behaviors) >= 1

    def test_finds_missed_evidence(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        # Dimensions with score < 0.5 and failures should appear
        assert len(report.missed_evidence) >= 1

    def test_identifies_unnecessary_actions(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        # Add repeated actions
        sid = uuid.UUID(session_id)
        repeated_events = list(sample_events)
        for i in range(5):
            repeated_events.append(
                SimulationEvent(
                    event_id=uuid.uuid4(),
                    session_id=sid,
                    sequence=len(repeated_events),
                    timestamp=datetime(2025, 1, 5 + i, tzinfo=UTC),
                    actor_type="participant",
                    event_type="action.executed",
                    payload={"action_type": "chat_message"},
                )
            )

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=repeated_events,
            final_state=state,
        )

        assert len(report.unnecessary_actions) >= 1  # chat_message repeated

    def test_extracts_critical_decisions(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        assert len(report.critical_decision_points) >= 1  # request_approval

    def test_counts_assumption_revisions(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        assert report.assumption_revisions == 1  # revise_assumption

    def test_evaluator_confidence_is_computed(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        assert 0.0 <= report.evaluator_confidence <= 1.0
        # Average of: 0.85, 0.6, 0.4, 0.7, 0.5, 0.3 = 3.35/6 ≈ 0.5583
        assert report.evaluator_confidence == pytest.approx(0.5583, abs=0.01)

    def test_empty_events_does_not_crash(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=[],
            final_state=state,
        )

        assert report.assumption_revisions == 0
        assert report.critical_decision_points == []
        assert report.governance_decisions == []

    def test_generates_alternative_trajectory(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        assert isinstance(report.alternative_valid_trajectory, str)
        assert len(report.alternative_valid_trajectory) > 0

    def test_generates_counterfactual(
        self,
        session_id,
        minimal_case,
        sample_dimension_scores,
        sample_violations,
        sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        assert isinstance(report.counterfactual_improvement, str)
        assert len(report.counterfactual_improvement) > 0

    def test_report_is_frozen(
        self, session_id, minimal_case, sample_dimension_scores,
        sample_violations, sample_events,
    ):
        service = ReportService()
        state = CanonicalState(budget_remaining=1000.0)

        report = service.generate_report(
            session_id=session_id,
            case_definition=minimal_case,
            dimension_scores=sample_dimension_scores,
            hard_constraint_outcomes=sample_violations,
            events=sample_events,
            final_state=state,
        )

        assert report.model_config.get("frozen") is True
