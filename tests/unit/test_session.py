"""Tests for SimulationSession and SessionStatus state transitions."""

from __future__ import annotations

import pytest
from afcs_domain.session import SessionStatus, SimulationSession
from pydantic import ValidationError


def test_session_creation_defaults() -> None:
    """A new session starts in CREATED status with sequence 0."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    assert session.status == SessionStatus.CREATED
    assert session.current_sequence == 0
    assert session.completed_at is None
    assert session.participant_id is None


def test_session_start_transition() -> None:
    """CREATED -> IN_PROGRESS succeeds and sets started_at."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    session.start()
    assert session.status == SessionStatus.IN_PROGRESS


def test_session_start_requires_created() -> None:
    """Starting a session that's already in_progress raises."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    session.start()
    with pytest.raises(ValueError, match="expected CREATED"):
        session.start()


def test_session_complete_transition() -> None:
    """IN_PROGRESS -> COMPLETED succeeds and sets completed_at."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    session.start()
    session.complete()
    assert session.status == SessionStatus.COMPLETED
    assert session.completed_at is not None


def test_session_complete_requires_in_progress() -> None:
    """Completing a CREATED session raises."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    with pytest.raises(ValueError, match="expected IN_PROGRESS"):
        session.complete()


def test_session_fail_transition() -> None:
    """Sessions can fail from any terminal-eligible status."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    session.fail()
    assert session.status == SessionStatus.FAILED


def test_session_mark_evaluated() -> None:
    """COMPLETED -> EVALUATED succeeds."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    session.start()
    session.complete()
    session.mark_evaluated()
    assert session.status == SessionStatus.EVALUATED


def test_mark_evaluated_requires_completed() -> None:
    """Can't mark a CREATED session as evaluated."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    with pytest.raises(ValueError, match="expected COMPLETED"):
        session.mark_evaluated()


def test_full_lifecycle() -> None:
    """CREATED -> IN_PROGRESS -> COMPLETED -> EVALUATED."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    assert session.status == SessionStatus.CREATED
    session.start()
    assert session.status == SessionStatus.IN_PROGRESS
    session.complete()
    assert session.status == SessionStatus.COMPLETED
    session.mark_evaluated()
    assert session.status == SessionStatus.EVALUATED


def test_increment_sequence() -> None:
    """increment_sequence advances the counter and returns the new value."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    assert session.increment_sequence() == 1
    assert session.increment_sequence() == 2
    assert session.current_sequence == 2


def test_valid_transitions_created() -> None:
    """CREATED can go to IN_PROGRESS or FAILED."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    transitions = session.valid_transitions()
    assert SessionStatus.IN_PROGRESS in transitions
    assert SessionStatus.FAILED in transitions


def test_valid_transitions_in_progress() -> None:
    """IN_PROGRESS can go to COMPLETED or FAILED."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    session.start()
    transitions = session.valid_transitions()
    assert SessionStatus.COMPLETED in transitions
    assert SessionStatus.FAILED in transitions


def test_valid_transitions_completed() -> None:
    """COMPLETED can only go to EVALUATED."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    session.start()
    session.complete()
    transitions = session.valid_transitions()
    assert transitions == [SessionStatus.EVALUATED]


def test_valid_transitions_terminal() -> None:
    """EVALUATED and FAILED have no outgoing transitions."""
    session = SimulationSession(case_id="case_test", case_version="1.0.0")
    session.start()
    session.complete()
    session.mark_evaluated()
    assert session.valid_transitions() == []

    failed = SimulationSession(case_id="case_test", case_version="1.0.0")
    failed.fail()
    assert failed.valid_transitions() == []


def test_session_rejects_extra_fields() -> None:
    """SimulationSession has forbid extra."""
    with pytest.raises(ValidationError):
        SimulationSession(
            case_id="case_test",
            case_version="1.0.0",
            unknown_field="boom",  # type: ignore[call-arg]
        )
