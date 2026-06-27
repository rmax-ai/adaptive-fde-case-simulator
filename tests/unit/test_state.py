"""Tests for CanonicalState, ParticipantVisibleState, to_visible."""

from __future__ import annotations

from afcs_domain.state import (
    CanonicalState,
    ParticipantVisibleState,
    StateDelta,
    to_visible,
)


def test_canonical_state_defaults() -> None:
    """CanonicalState has sensible defaults."""
    state = CanonicalState()
    assert state.phase == "unknown"
    assert state.budget_remaining == 0.0
    assert state.artifacts == []
    assert state.stakeholder_relationships == {}
    assert state.flags == {}
    assert state.hidden_context == {}
    assert state.evaluation_criteria == {}
    assert state.risk_assessment == {}
    assert state.correct_solution is None
    assert state.metadata == {}


def test_visible_state_defaults() -> None:
    """ParticipantVisibleState has sensible defaults and no hidden fields."""
    state = ParticipantVisibleState()
    assert state.phase == "unknown"
    assert state.budget_remaining == 0.0
    assert state.artifacts == []
    assert state.stakeholder_relationships == {}
    assert state.flags == {}
    assert state.metadata == {}

    # Ensure hidden fields are NOT present
    assert not hasattr(state, "hidden_context")
    assert not hasattr(state, "risk_assessment")
    assert not hasattr(state, "correct_solution")
    assert not hasattr(state, "evaluation_criteria")


def test_to_visible_projects_only_public_fields() -> None:
    """to_visible() must never leak hidden fields into the visible view."""
    canonical = CanonicalState(
        phase="deploy",
        budget_remaining=25000.0,
        artifacts=[{"name": "deploy.yaml", "type": "yaml"}],
        stakeholder_relationships={"cto": 80},
        flags={"has_warned": False},
        hidden_context={"secret_key": "s3cr3t"},
        evaluation_criteria={"discovery_weight": 0.30},
        risk_assessment={"level": "high"},
        correct_solution="Use rule-based engine",
        metadata={"started_at": "2025-01-01"},
    )

    visible = to_visible(canonical)

    assert isinstance(visible, ParticipantVisibleState)
    assert visible.phase == "deploy"
    assert visible.budget_remaining == 25000.0
    assert visible.artifacts == [{"name": "deploy.yaml", "type": "yaml"}]
    assert visible.stakeholder_relationships == {"cto": 80}
    assert visible.flags == {"has_warned": False}
    assert visible.metadata == {"started_at": "2025-01-01"}

    # Hidden fields must not be accessible
    assert not hasattr(visible, "hidden_context")
    assert not hasattr(visible, "risk_assessment")
    assert not hasattr(visible, "correct_solution")
    assert not hasattr(visible, "evaluation_criteria")


def test_to_visible_preserves_artifacts_independence() -> None:
    """Modifying visible artifacts should not affect canonical artifacts."""
    canonical = CanonicalState(
        artifacts=[{"name": "doc.md", "type": "md"}],
    )
    visible = to_visible(canonical)
    visible.artifacts.append({"name": "leaked.txt", "type": "txt"})
    assert len(canonical.artifacts) == 1
    assert len(visible.artifacts) == 2


def test_to_visible_with_empty_canonical() -> None:
    """to_visible handles a default CanonicalState gracefully."""
    canonical = CanonicalState()
    visible = to_visible(canonical)
    assert visible.phase == "unknown"
    assert visible.budget_remaining == 0.0
    assert visible.artifacts == []
    assert visible.stakeholder_relationships == {}
    assert visible.flags == {}
    assert visible.metadata == {}


def test_canonical_as_dict_serializes_all_fields() -> None:
    """as_dict() produces a JSON-safe representation."""
    canonical = CanonicalState(
        phase="discovery",
        budget_remaining=50000.0,
        correct_solution="Reroute to non-AI",
    )
    d = canonical.as_dict()
    assert d["phase"] == "discovery"
    assert d["budget_remaining"] == 50000.0
    assert d["correct_solution"] == "Reroute to non-AI"
    assert "hidden_context" in d


def test_visible_as_dict_excludes_hidden() -> None:
    """Visible state's as_dict() should not contain hidden fields."""
    canonical = CanonicalState(
        phase="discovery",
        correct_solution="Reroute",
        risk_assessment={"level": "high"},
    )
    visible = to_visible(canonical)
    d = visible.as_dict()
    assert d["phase"] == "discovery"
    assert "correct_solution" not in d
    assert "risk_assessment" not in d
    assert "evaluation_criteria" not in d
    assert "hidden_context" not in d


def test_state_delta_creation() -> None:
    """StateDelta correctly stores a single atomic change."""
    delta = StateDelta(
        path="budget_remaining",
        operation="set",
        value=45000.0,
        previous_value=50000.0,
    )
    assert delta.path == "budget_remaining"
    assert delta.operation == "set"
    assert delta.value == 45000.0
    assert delta.previous_value == 50000.0
