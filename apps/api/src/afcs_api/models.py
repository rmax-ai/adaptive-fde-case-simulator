"""SQLAlchemy ORM models for the AFCS API.

Tables:
- CaseRecord: persisted case definitions
- SessionRecord: simulation sessions
- EventRecord: append-only event stream
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from afcs_api.db import Base

if TYPE_CHECKING:
    from afcs_domain import SimulationEvent


class CaseRecord(Base):
    """Persisted case definition metadata + schema."""

    __tablename__ = "case_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    schema_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    # no relationship to SessionRecord — cross-table via string columns, no FK constraint


class SessionRecord(Base):
    """A single simulation session run."""

    __tablename__ = "session_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    case_version: Mapped[str] = mapped_column(String(50), nullable=False)
    participant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created")
    current_state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    current_sequence: Mapped[int] = mapped_column(default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # relationships
    events: Mapped[list[EventRecord]] = relationship(
        "EventRecord", back_populates="session", lazy="selectin"
    )


class EventRecord(Base):
    """Immutable event in the session event stream."""

    __tablename__ = "event_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("session_records.id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    pre_state_hash: Mapped[str] = mapped_column(Text, nullable=False, default="")
    post_state_hash: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    # relationships
    session: Mapped[SessionRecord] = relationship("SessionRecord", back_populates="events")

    def to_domain_event(self) -> SimulationEvent:
        """Convert this EventRecord to a domain SimulationEvent."""
        return SimulationEvent(
            event_id=self.id,
            session_id=self.session_id,
            sequence=self.sequence,
            timestamp=self.created_at,
            actor_type=self.actor_type,
            actor_id=self.actor_id,
            event_type=self.event_type,
            payload=self.payload,
            pre_state_hash=self.pre_state_hash,
            post_state_hash=self.post_state_hash,
        )
