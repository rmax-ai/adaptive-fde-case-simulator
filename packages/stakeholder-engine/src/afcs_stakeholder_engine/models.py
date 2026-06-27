from __future__ import annotations

from pydantic import BaseModel, Field


class ResponseDirective(BaseModel):
    """Deterministic policy decision directing how a stakeholder should respond."""

    allowed_facts: list[str] = Field(default_factory=list)
    """Facts the stakeholder can reference in their response."""

    prohibited_topics: list[str] = Field(default_factory=list)
    """Topics the stakeholder must avoid discussing."""

    required_tone: str = "neutral"
    """One of: formal, concerned, encouraging, neutral, skeptical."""

    response_category: str = "deflect"
    """One of: approve, reject, request_info, escalate, deflect."""

    max_reveal_depth: int = 0
    """0=nothing new, 1=surface, 2=moderate detail."""

    trust_change: float = 0.0
    """Delta to apply to the stakeholder's trust score."""

    escalate: bool = False
    """Whether to trigger escalation to a higher authority."""


class StakeholderResponse(BaseModel):
    """The rendered natural-language response from a stakeholder."""

    message: str
    """The natural language response text."""

    disclosed_fact_ids: list[str] = Field(default_factory=list)
    """IDs of facts disclosed in this response."""

    tone: str = "neutral"
    """The tone used in the response."""

    policy_decision_id: str = ""
    """Identifier linking this response to the policy decision that shaped it."""
