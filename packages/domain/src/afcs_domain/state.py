from __future__ import annotations

from pydantic import BaseModel, Field


class CanonicalState(BaseModel):
    """The full internal simulation state — hidden fields + visible fields.

    This is the authoritative representation of "what is really happening"
    in the simulation.  It is never exposed directly to participants; only
    projected views (ParticipantVisibleState) are shown.
    """

    phase: str = "unknown"
    budget_remaining: float = 0.0
    artifacts: list[dict] = Field(default_factory=list)
    stakeholder_relationships: dict[str, float] = Field(default_factory=dict)
    flags: dict[str, bool] = Field(default_factory=dict)
    hidden_context: dict = Field(default_factory=dict)
    evaluation_criteria: dict = Field(default_factory=dict)
    risk_assessment: dict = Field(default_factory=dict)
    correct_solution: str | None = None
    metadata: dict = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    def as_dict(self) -> dict:
        return self.model_dump(mode="json")


class ParticipantVisibleState(BaseModel):
    """The projected view of simulation state shown to participants.

    This deliberately excludes hidden fields such as `hidden_context`,
    `risk_assessment`, `correct_solution`, and internal `evaluation_criteria`.
    """

    phase: str = "unknown"
    budget_remaining: float = 0.0
    artifacts: list[dict] = Field(default_factory=list)
    stakeholder_relationships: dict[str, float] = Field(default_factory=dict)
    flags: dict[str, bool] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    def as_dict(self) -> dict:
        return self.model_dump(mode="json")


class StateDelta(BaseModel):
    """A diff representation applied during a state transition.

    Each entry describes one atomic change to the canonical state.
    """

    path: str  # e.g. "phase", "budget_remaining", "flags.has_warned"
    operation: str  # "set", "unset", "append", "increment"
    value: object = None
    previous_value: object = None

    model_config = {"extra": "forbid"}


def to_visible(canonical: CanonicalState) -> ParticipantVisibleState:
    """Project a CanonicalState into a ParticipantVisibleState.

    Hidden fields (hidden_context, risk_assessment, correct_solution,
    evaluation_criteria) are never leaked into the visible view.
    """
    return ParticipantVisibleState(
        phase=canonical.phase,
        budget_remaining=canonical.budget_remaining,
        artifacts=list(canonical.artifacts),
        stakeholder_relationships=dict(canonical.stakeholder_relationships),
        flags=dict(canonical.flags),
        metadata=dict(canonical.metadata),
    )
