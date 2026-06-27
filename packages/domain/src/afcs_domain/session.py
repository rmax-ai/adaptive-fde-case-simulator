from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SessionStatus(StrEnum):
    """Lifecycle states of a simulation session."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EVALUATED = "evaluated"
    FAILED = "failed"


class SimulationSession(BaseModel):
    """The run-time representation of a single simulation session.

    Holds the canonical state blob, participant binding, and progression
    metadata.  The `current_state` dict is the full hidden+visible state
    as it exists after the most recently applied event.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    case_id: str
    case_version: str
    participant_id: uuid.UUID | None = None
    status: SessionStatus = SessionStatus.CREATED
    current_state: dict = Field(default_factory=dict)
    current_sequence: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    model_config = {"extra": "forbid"}

    def start(self) -> None:
        """Transition session from CREATED to IN_PROGRESS."""
        if self.status != SessionStatus.CREATED:
            raise ValueError(
                f"Cannot start session with status {self.status.value}; expected CREATED"
            )
        self.status = SessionStatus.IN_PROGRESS
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        """Transition session from IN_PROGRESS to COMPLETED."""
        if self.status != SessionStatus.IN_PROGRESS:
            raise ValueError(
                f"Cannot complete session with status {self.status.value}; expected IN_PROGRESS"
            )
        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def fail(self, message: str = "") -> None:
        """Mark the session as FAILED from any terminal-eligible status."""
        self.status = SessionStatus.FAILED
        self.completed_at = datetime.now(UTC)

    def mark_evaluated(self) -> None:
        """Transition from COMPLETED to EVALUATED."""
        if self.status != SessionStatus.COMPLETED:
            raise ValueError(
                f"Cannot mark session as evaluated with status "
                f"{self.status.value}; expected COMPLETED"
            )
        self.status = SessionStatus.EVALUATED

    def increment_sequence(self) -> int:
        """Advance the event sequence counter, returning the new value."""
        self.current_sequence += 1
        return self.current_sequence

    def valid_transitions(self) -> list[SessionStatus]:
        """Return the set of statuses this session can transition to."""
        _transitions: dict[SessionStatus, list[SessionStatus]] = {
            SessionStatus.CREATED: [SessionStatus.IN_PROGRESS, SessionStatus.FAILED],
            SessionStatus.IN_PROGRESS: [SessionStatus.COMPLETED, SessionStatus.FAILED],
            SessionStatus.COMPLETED: [SessionStatus.EVALUATED],
            SessionStatus.EVALUATED: [],
            SessionStatus.FAILED: [],
        }
        return list(_transitions.get(self.status, []))
