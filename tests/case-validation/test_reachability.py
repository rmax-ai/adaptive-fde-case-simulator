"""Tests for reachability checker."""

from __future__ import annotations

from afcs_case_schema.models import (
    ActionDefinition,
    ActionRegistry,
    BusinessState,
    CaseDefinition,
    CaseMetadata,
    CaseStatus,
    DifficultyLevel,
    EvaluationConfig,
    EvaluationDimension,
    EvidenceManifest,
    GovernanceState,
    OrganizationalState,
    StakeholderConfig,
    TechnicalState,
    TimelineConfig,
)
from afcs_case_schema.reachability import check_reachability, ReachabilityChecker


def _make_case_def(
    target_facts: list[str] | None = None,
    hidden_defects: list[str] | None = None,
    action_types: list[str] | None = None,
) -> CaseDefinition:
    """Create a minimal CaseDefinition for testing."""
    return CaseDefinition(
        metadata=CaseMetadata(
            case_id="test_case",
            version="1.0.0",
            title="Test Case",
            domain="test",
            status=CaseStatus.published,
            difficulty=DifficultyLevel.intermediate,
        ),
        business=BusinessState(
            stated_goal="Test business goal",
            business_risks=["Risk of test failure"],
        ),
        technical=TechnicalState(
            hidden_defects=hidden_defects or [],
            technical_constraints=["Must use test framework"],
        ),
        organization=OrganizationalState(
            stakeholders=[
                StakeholderConfig(
                    stakeholder_id="test-stakeholder",
                    role="Tester",
                    hidden_incentives=["Needs to complete all tests"],
                    knowledge=["Test procedure", "Test data"],
                    false_beliefs=["All tests pass on first run"],
                )
            ]
        ),
        governance=GovernanceState(
            data_classification="public",
            applicable_policies=[],
            approval_rules=[],
            human_review_boundaries=[],
            audit_requirements=[],
            forbidden_actions=[],
        ),
        timeline=TimelineConfig(),
        evidence=EvidenceManifest(),
        actions=ActionRegistry(
            allowed=[
                ActionDefinition(action_type=at, parameter_schema={})
                for at in (action_types or ["chat_message", "upload_artifact"])
            ]
        ),
        evaluation=EvaluationConfig(
            dimensions=[
                EvaluationDimension(
                    name="discovery", weight=0.6, criteria=["Test criterion A"]
                ),
                EvaluationDimension(
                    name="delivery",
                    weight=0.4,
                    criteria=["Deliver final report", "Document findings"],
                ),
            ],
            target_facts=target_facts or [],
        ),
    )


# ---------------------------------------------------------------------------
# Reachable facts
# ---------------------------------------------------------------------------


def test_reachable_hidden_defect() -> None:
    """A target fact matching a hidden_defect should be reachable."""
    case_def = _make_case_def(
        target_facts=["hidden_defect_xyz"],
        hidden_defects=["hidden_defect_xyz"],
    )
    result = check_reachability(case_def)
    assert result.all_reachable, f"Errors: {result.errors}, unreachable: {result.unreachable_facts}"
    assert result.reachable["hidden_defect_xyz"] is True


def test_reachable_dimension_name() -> None:
    """A target fact matching an evaluation dimension name should be reachable."""
    case_def = _make_case_def(target_facts=["discovery"])
    result = check_reachability(case_def)
    assert result.all_reachable
    assert result.reachable["discovery"] is True


def test_reachable_action_type() -> None:
    """A target fact matching an action type should be reachable."""
    case_def = _make_case_def(
        target_facts=["chat_message"],
        action_types=["chat_message", "upload_artifact"],
    )
    result = check_reachability(case_def)
    assert result.all_reachable


def test_reachable_stakeholder_incentive() -> None:
    """Target facts matching stakeholder hidden_incentives should be reachable."""
    case_def = _make_case_def(
        target_facts=["Needs_to_complete_all_tests"],
    )
    result = check_reachability(case_def)
    assert result.all_reachable


def test_reachable_stakeholder_belief() -> None:
    """Target facts matching stakeholder false_beliefs should be reachable."""
    case_def = _make_case_def(
        target_facts=["All_tests_pass_on_first_run"],
    )
    result = check_reachability(case_def)
    assert result.all_reachable


def test_reachable_stakeholder_knowledge() -> None:
    """Target facts matching stakeholder knowledge should be reachable."""
    case_def = _make_case_def(
        target_facts=["Test_procedure"],
    )
    result = check_reachability(case_def)
    assert result.all_reachable


def test_reachable_criterion_text() -> None:
    """Target facts matching evaluation criteria should be reachable."""
    case_def = _make_case_def(
        target_facts=["Deliver_final_report"],
    )
    result = check_reachability(case_def)
    assert result.all_reachable


# ---------------------------------------------------------------------------
# Unreachable facts
# ---------------------------------------------------------------------------


def test_unreachable_fact() -> None:
    """A target fact with no match should be unreachable."""
    case_def = _make_case_def(target_facts=["nonexistent_fact_xyz"])
    result = check_reachability(case_def)
    assert not result.all_reachable
    assert "nonexistent_fact_xyz" in result.unreachable_facts


def test_empty_target_facts() -> None:
    """Empty target_facts should produce an error/warning."""
    case_def = _make_case_def(target_facts=[])
    result = check_reachability(case_def)
    assert result.all_reachable  # vacuously true
    assert result.errors  # but should have error about no target facts


def test_multiple_unreachable() -> None:
    """Multiple unreachable facts should all be reported."""
    case_def = _make_case_def(target_facts=["a", "b", "c"])
    result = check_reachability(case_def)
    assert not result.all_reachable
    assert len(result.unreachable_facts) == 3


# ---------------------------------------------------------------------------
# Mixed reachable and unreachable
# ---------------------------------------------------------------------------


def test_mixed_reachability() -> None:
    """Some reachable, some unreachable facts."""
    case_def = _make_case_def(
        target_facts=["discovery", "fictional_fact"],
    )
    result = check_reachability(case_def)
    assert not result.all_reachable
    assert result.reachable["discovery"] is True
    assert "fictional_fact" in result.unreachable_facts


# ---------------------------------------------------------------------------
# ReachabilityChecker class
# ---------------------------------------------------------------------------


def test_reachability_checker_class() -> None:
    """ReachabilityChecker.check should work."""
    case_def = _make_case_def(
        target_facts=["delivery"],
    )
    result = ReachabilityChecker.check(case_def)
    assert result.all_reachable
    assert result.reachable["delivery"] is True


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


def test_summary_all_pass() -> None:
    """Summary should report PASS for all-reachable."""
    case_def = _make_case_def(
        target_facts=["discovery"],
    )
    result = check_reachability(case_def)
    summary = result.summary()
    assert "reachable" in summary.lower() or "ALL" in summary


def test_summary_reports_unreachable() -> None:
    """Summary should list unreachable facts."""
    case_def = _make_case_def(target_facts=["phantasm"])
    result = check_reachability(case_def)
    summary = result.summary()
    assert "phantasm" in summary
