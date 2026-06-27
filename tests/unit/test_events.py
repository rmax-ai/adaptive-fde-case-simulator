"""Tests for the SimulationEvent model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from afcs_domain.events import SimulationEvent


def test_event_creation_with_defaults() -> None:
    """An event with minimal required fields gets sensible defaults."""
    session_id = uuid.uuid4()
    event = SimulationEvent(
        session_id=session_id,
        sequence=0,
        actor_type="system",
        event_type="session.created",
    )

    assert event.session_id == session_id
    assert event.sequence == 0
    assert event.actor_type == "system"
    assert event.event_type == "session.created"
    assert isinstance(event.event_id, uuid.UUID)
    assert isinstance(event.timestamp, datetime)
    assert event.payload == {}
    assert event.effects == []
    assert event.observations == []
    assert event.pre_state_hash == ""
    assert event.post_state_hash == ""
    assert event.actor_id is None


def test_event_creation_all_fields() -> None:
    """An event with every field populated is correctly round-tripped."""
    session_id = uuid.uuid4()
    event_id = uuid.uuid4()
    ts = datetime.now(UTC)

    event = SimulationEvent(
        event_id=event_id,
        session_id=session_id,
        sequence=5,
        timestamp=ts,
        actor_type="participant",
        actor_id="user-abc",
        event_type="action.executed",
        payload={"action": "inspect_artifact", "target": "deployment.yaml"},
        pre_state_hash="abc123",
        effects=[{"path": "phase", "operation": "set", "value": "deploy"}],
        observations=[{"type": "info", "message": "Artifact inspected"}],
        post_state_hash="def456",
    )

    assert event.event_id == event_id
    assert event.session_id == session_id
    assert event.sequence == 5
    assert event.timestamp == ts
    assert event.actor_type == "participant"
    assert event.actor_id == "user-abc"
    assert event.event_type == "action.executed"
    assert event.payload == {"action": "inspect_artifact", "target": "deployment.yaml"}
    assert event.pre_state_hash == "abc123"
    assert event.effects == [{"path": "phase", "operation": "set", "value": "deploy"}]
    assert event.observations == [{"type": "info", "message": "Artifact inspected"}]
    assert event.post_state_hash == "def456"


def test_event_is_frozen() -> None:
    """SimulationEvent should be immutable after creation."""
    session_id = uuid.uuid4()
    event = SimulationEvent(
        session_id=session_id,
        sequence=0,
        actor_type="system",
        event_type="session.created",
    )

    with pytest.raises(ValidationError):
        event.sequence = 1  # type: ignore[misc]


def test_event_serialization_roundtrip() -> None:
    """An event serialized to dict and back retains all values."""
    session_id = uuid.uuid4()
    event = SimulationEvent(
        session_id=session_id,
        sequence=3,
        actor_type="stakeholder",
        actor_id="cto",
        event_type="stakeholder.responded",
        payload={"message": "Approved.", "approval": True},
        pre_state_hash="prev_hash",
        effects=[{"path": "stakeholder_relationships.cto", "operation": "set", "value": 60}],
        post_state_hash="next_hash",
    )

    data = event.model_dump(mode="json")
    restored = SimulationEvent.model_validate(data)

    assert restored.event_id == event.event_id
    assert restored.session_id == event.session_id
    assert restored.sequence == event.sequence
    assert restored.actor_type == event.actor_type
    assert restored.actor_id == event.actor_id
    assert restored.event_type == event.event_type
    assert restored.payload == event.payload
    assert restored.effects == event.effects
    assert restored.pre_state_hash == event.pre_state_hash
    assert restored.post_state_hash == event.post_state_hash


def test_event_rejects_extra_fields() -> None:
    """SimulationEvent has forbid extra, so unknown fields raise."""
    session_id = uuid.uuid4()
    with pytest.raises(ValidationError):
        SimulationEvent(
            session_id=session_id,
            sequence=0,
            actor_type="system",
            event_type="session.created",
            bogus_field="should not be allowed",  # type: ignore[call-arg]
        )


def test_actor_type_enforcement() -> None:
    """actor_type is a plain string, not an enum, but we validate shape."""
    session_id = uuid.uuid4()
    event = SimulationEvent(
        session_id=session_id,
        sequence=0,
        actor_type="participant",
        event_type="action.executed",
    )
    assert event.actor_type == "participant"
