"""Tests for state transition determinism and phase gating."""

from __future__ import annotations

from copy import deepcopy

import pytest

from afcs_simulation_engine import StateTransitionEngine
from afcs_simulation_engine.state_hash import compute_state_hash


def test_deterministic_transitions(engine: StateTransitionEngine) -> None:
    """Given same (state, action), handler always produces same new_state."""
    state1 = {"phase": "discovery", "budget_remaining": 50000, "artifacts_inspected": []}
    state2 = deepcopy(state1)

    handler = engine.registry.get_handler("inspect_artifact")
    assert handler is not None

    result1 = handler(state1, {"artifact_id": "doc1"})
    result2 = handler(state2, {"artifact_id": "doc1"})

    assert compute_state_hash(result1) == compute_state_hash(result2)


def test_deterministic_full_path(engine: StateTransitionEngine, session_in_progress) -> None:
    """Executing the same action twice produces identical events (hashes)."""
    from copy import deepcopy

    s1 = deepcopy(session_in_progress)
    s2 = deepcopy(session_in_progress)

    event1, _ = engine.execute_action(s1, "inspect_artifact", {"artifact_id": "deploy.yaml"})
    event2, _ = engine.execute_action(s2, "inspect_artifact", {"artifact_id": "deploy.yaml"})

    assert event1.post_state_hash == event2.post_state_hash
    assert event1.pre_state_hash == event2.pre_state_hash


def test_phase_gating_prevents_early_action(engine: StateTransitionEngine, session_in_progress) -> None:
    """submit_final_recommendation is blocked before reporting phase."""
    failed = engine.validate_action(session_in_progress, "submit_final_recommendation", {})
    assert len(failed) > 0
    assert any("requires phase 'reporting'" in f for f in failed)


def test_budget_tracking(engine: StateTransitionEngine, session_in_progress) -> None:
    """Actions with budget costs reduce budget_remaining."""
    # Advance to architecture phase so run_analysis is valid
    session_in_progress.current_state["phase"] = "architecture"
    before = session_in_progress.current_state.get("budget_remaining", 50000)
    engine.execute_action(session_in_progress, "run_analysis", {"findings": "test", "cost": 1000})
    after = session_in_progress.current_state.get("budget_remaining", 0)
    assert after == before - 1000


def test_state_hash_changes_on_action(engine: StateTransitionEngine, session_in_progress) -> None:
    """Each action produces a new state hash."""
    pre = compute_state_hash(session_in_progress.current_state)
    engine.execute_action(session_in_progress, "inspect_artifact", {"artifact_id": "doc1"})
    post = compute_state_hash(session_in_progress.current_state)
    assert pre != post


def test_submit_final_completes_session(engine: StateTransitionEngine, session_in_progress) -> None:
    """submit_final_recommendation transitions status to completed."""
    # Override phase to reporting
    session_in_progress.current_state["phase"] = "reporting"
    _, updated = engine.execute_action(
        session_in_progress,
        "submit_final_recommendation",
        {"summary": "Done", "recommendation": "Proceed"},
    )
    assert updated.current_state.get("status") == "completed"
