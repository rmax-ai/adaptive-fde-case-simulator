"""Tests for event replay producing identical state."""

from __future__ import annotations

from copy import deepcopy

import pytest

from afcs_domain import SimulationEvent
from afcs_simulation_engine import StateTransitionEngine
from afcs_simulation_engine.state_hash import compute_state_hash


def test_replay_from_events_produces_identical_state(
    engine: StateTransitionEngine,
    session_in_progress,
) -> None:
    """Replaying the event stream produces the same final state as executing
    the actions live."""
    session = deepcopy(session_in_progress)

    # Execute a sequence of actions
    actions = [
        ("inspect_artifact", {"artifact_id": "deploy.yaml"}),
        ("ask_stakeholder", {"stakeholder_id": "cto", "question": "Status?"}),
        ("register_assumption", {"id": "a1", "description": "API stable"}),
        ("register_risk", {"id": "r1", "description": "Budget risk"}),
    ]

    events: list[SimulationEvent] = []
    for action_type, params in actions:
        event, session = engine.execute_action(session, action_type, params)
        events.append(event)

    live_hash = compute_state_hash(session.current_state)

    # Now replay from initial state using recorded events
    replayed_session = engine.replay_events(events)
    replay_hash = compute_state_hash(replayed_session.current_state)

    assert live_hash == replay_hash, "Replay produced different state than live execution"


def test_replay_empty_events(engine: StateTransitionEngine) -> None:
    """Replaying an empty event list returns the initial state."""
    session = engine.replay_events([])
    assert session.current_sequence == 0
    assert session.current_state.get("phase") == "discovery"


def test_replay_deterministic(engine: StateTransitionEngine, session_in_progress) -> None:
    """Replaying the same events twice produces identical state."""
    session = deepcopy(session_in_progress)

    actions = [
        ("inspect_artifact", {"artifact_id": "doc1"}),
        ("define_baseline", {"description": "Current metrics"}),
    ]

    events: list[SimulationEvent] = []
    for action_type, params in actions:
        event, session = engine.execute_action(session, action_type, params)
        events.append(event)

    session1 = engine.replay_events(events)
    session2 = engine.replay_events(events)

    h1 = compute_state_hash(session1.current_state)
    h2 = compute_state_hash(session2.current_state)
    assert h1 == h2


def test_replay_rejects_out_of_order(engine: StateTransitionEngine) -> None:
    """Replay raises ValueError for non-monotonic sequences."""
    from uuid import uuid4
    sid = uuid4()
    events = [
        SimulationEvent(session_id=sid, sequence=1, event_type="action_executed",
                        actor_type="participant", payload={"action_type": "inspect_artifact", "params": {}}),
        SimulationEvent(session_id=sid, sequence=0, event_type="action_executed",
                        actor_type="participant", payload={"action_type": "inspect_artifact", "params": {}}),
    ]
    with pytest.raises(ValueError, match="sequence gap"):
        engine.replay_events(events)


def test_replay_with_pre_state_hash_integrity(engine: StateTransitionEngine, session_in_progress) -> None:
    """Each event's pre-state hash should match the post-state hash of the prior event."""
    session = deepcopy(session_in_progress)
    initial_hash = compute_state_hash(session.current_state)
    actions = [
        ("inspect_artifact", {"artifact_id": "doc1"}),
        ("register_assumption", {"id": "a1", "description": "test"}),
        ("register_risk", {"id": "r1", "description": "risk"}),
    ]
    events: list[SimulationEvent] = []
    for action_type, params in actions:
        event, session = engine.execute_action(session, action_type, params)
        events.append(event)

    # First event pre_hash is initial state
    assert events[0].pre_state_hash == initial_hash

    for i, event in enumerate(events):
        if i == 0:
            continue
        prev = events[i - 1]
        assert event.pre_state_hash == prev.post_state_hash, (
            f"Event {i} pre-state hash doesn't match event {i-1} post-state hash"
        )
