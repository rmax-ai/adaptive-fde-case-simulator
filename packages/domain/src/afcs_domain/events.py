from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SimulationEvent(BaseModel):
    """A single, immutable event in the simulation event stream.

    Every state-changing action in the simulation produces exactly one
    SimulationEvent.  Events are append-only and form the full audit trail
    from which canonical state can always be reconstructed.
    """

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    session_id: uuid.UUID
    sequence: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor_type: str  # 'participant', 'system', 'stakeholder'
    actor_id: str | None = None
    event_type: str  # 'session.created', 'action.executed', 'stakeholder.responded', etc.
    payload: dict = Field(default_factory=dict)
    pre_state_hash: str = ""
    effects: list[dict] = Field(default_factory=list)  # [{path, operation, value}, ...]
    observations: list[dict] = Field(default_factory=list)
    post_state_hash: str = ""

    model_config = {"extra": "forbid", "frozen": True}
