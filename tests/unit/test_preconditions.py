"""Tests for precondition validation on the StateTransitionEngine."""

from __future__ import annotations

import pytest
from afcs_domain import PreconditionError


def test_unknown_action_fails_precondition(engine, session_in_progress) -> None:
    """An unregistered action type is rejected."""
    failed = engine.validate_action(session_in_progress, "nonexistent_action", {})
    assert len(failed) > 0
    assert any("Unknown action type" in f for f in failed)


def test_session_must_be_in_progress(engine, session_in_progress) -> None:
    """A session that isn't IN_PROGRESS blocks all actions."""
    from afcs_domain import SessionStatus

    session_in_progress.status = SessionStatus.CREATED
    failed = engine.validate_action(session_in_progress, "inspect_artifact", {"artifact_id": "doc"})
    assert len(failed) > 0
    assert any("not in progress" in f.lower() for f in failed)


def test_completed_session_blocks_actions(engine, session_in_progress) -> None:
    """A completed session blocks further actions."""
    from afcs_domain import SessionStatus

    session_in_progress.status = SessionStatus.COMPLETED
    failed = engine.validate_action(session_in_progress, "inspect_artifact", {"artifact_id": "doc"})
    assert len(failed) > 0


def test_budget_exceeded_fails(engine, session_in_progress) -> None:
    """An action with budget cost exceeding remaining budget is blocked."""
    # Must be in delivery phase for run_pilot
    session_in_progress.current_state["phase"] = "delivery"
    session_in_progress.current_state["budget_remaining"] = 100
    failed = engine.validate_action(
        session_in_progress, "run_pilot", {"scope": "test", "cost": 5000}
    )
    assert len(failed) > 0
    assert any("Insufficient budget" in f for f in failed)


def test_execute_raises_on_failed_precondition(engine, session_in_progress) -> None:
    """execute_action raises PreconditionError when validation fails."""
    from afcs_domain import SessionStatus

    session_in_progress.status = SessionStatus.COMPLETED
    with pytest.raises(PreconditionError, match="Cannot execute"):
        engine.execute_action(session_in_progress, "inspect_artifact", {"artifact_id": "doc"})


def test_phase_gate_discovery_actions_work(engine, session_in_progress) -> None:
    """Discovery-phase actions should pass validation in discovery phase."""
    state = session_in_progress.current_state
    state["phase"] = "discovery"

    for action_type in [
        "inspect_artifact",
        "ask_stakeholder",
        "register_assumption",
        "register_risk",
    ]:
        failed = engine.validate_action(session_in_progress, action_type, {})
        assert len(failed) == 0, f"{action_type} should be valid in discovery"


def test_phase_gate_evaluation_blocks_in_discovery(engine, session_in_progress) -> None:
    """Evaluation-phase actions should fail in discovery phase."""
    state = session_in_progress.current_state
    state["phase"] = "discovery"

    for action_type in ["define_success_metric", "propose_scope"]:
        failed = engine.validate_action(session_in_progress, action_type, {})
        assert len(failed) > 0, f"{action_type} should be blocked in discovery"


def test_validate_action_returns_empty_for_valid(engine, session_in_progress) -> None:
    """A valid action returns an empty list."""
    failed = engine.validate_action(
        session_in_progress, "inspect_artifact", {"artifact_id": "doc1"}
    )
    assert failed == []
