from __future__ import annotations

import re
from typing import Any

from afcs_case_schema.models import CaseDefinition, StakeholderConfig

from afcs_stakeholder_engine.models import ResponseDirective

# ── Intent classification ─────────────────────────────────────────────────────


class MessageIntent:
    """Categorisation of a participant message."""

    QUESTION = "question"
    PROPOSAL = "proposal"
    REQUEST = "request"
    CHALLENGE = "challenge"
    STATEMENT = "statement"
    GREETING = "greeting"


_QUESTION_PATTERNS = re.compile(
    r"(what|how|why|when|where|who|which|can|could|would|will|is|are|do|does|did|should|"
    r"have|has|tell me|explain|describe|clarify)",
    re.IGNORECASE,
)
_PROPOSAL_PATTERNS = re.compile(
    r"(propose|suggest|recommend|let.s|we should|we could|i think we|how about|"
    r"what if|i.d like to|my plan|approach|strategy)",
    re.IGNORECASE,
)
_REQUEST_PATTERNS = re.compile(
    r"(i need|i want|please|request|require|access to|can you give|"
    r"share|provide me|give me)",
    re.IGNORECASE,
)
_CHALLENGE_PATTERNS = re.compile(
    r"(why (didn|haven|isn|aren|wasn)|this is wrong|i disagree|that.s incorrect|"
    r"that doesn.t make sense|wrong|problem|issue|concern|mistake|error|flaw)",
    re.IGNORECASE,
)
_GREETING_PATTERNS = re.compile(
    r"^(hi|hello|hey|good morning|good afternoon|good evening|greetings)",
    re.IGNORECASE,
)

# ── Trigger phrases for escalation ────────────────────────────────────────────

_ESCALATION_TRIGGERS = re.compile(
    r"(escalate|complaint|formal|legal|regulatory|lawyer|attorney|"
    r"lawsuit|breach|violation|unauthoriz|above your pay|security incident)",
    re.IGNORECASE,
)

# ── Hidden-information signals (asking about things outside knowledge) ────────


def _normalise(text: str) -> str:
    """Replace underscores with spaces for fuzzy content matching.

    Facts, beliefs, and rules often use underscores (e.g. ``third_party_api``)
    while participant messages use spaces (e.g. ``third party api``).
    """
    return text.lower().replace("_", " ")


def _classify_intent(message: str) -> str:
    """Classify a participant message into an intent category."""
    msg_stripped = message.strip()
    if _GREETING_PATTERNS.match(msg_stripped):
        return MessageIntent.GREETING
    if _CHALLENGE_PATTERNS.search(msg_stripped):
        return MessageIntent.CHALLENGE
    if _PROPOSAL_PATTERNS.search(msg_stripped):
        return MessageIntent.PROPOSAL
    if _REQUEST_PATTERNS.search(msg_stripped):
        return MessageIntent.REQUEST
    if _QUESTION_PATTERNS.search(msg_stripped):
        return MessageIntent.QUESTION
    return MessageIntent.STATEMENT


# ── The engine ────────────────────────────────────────────────────────────────


class StakeholderPolicyEngine:
    """Deterministic policy engine that evaluates participant actions
    against case-defined policy rules.

    This is pure logic — no LLM calls.  It produces a ``ResponseDirective``
    that the ``StakeholderLanguageRenderer`` then turns into natural language.
    """

    def __init__(
        self, stakeholder_config: StakeholderConfig, case_definition: CaseDefinition
    ) -> None:
        self._stakeholder = stakeholder_config
        self._case = case_definition

    @property
    def stakeholder(self) -> StakeholderConfig:
        return self._stakeholder

    @property
    def case(self) -> CaseDefinition:
        return self._case

    def evaluate(
        self,
        participant_message: str,
        current_state: dict[str, Any],
        conversation_history: list[dict[str, Any]],
    ) -> ResponseDirective:
        """Evaluate a participant message against policy rules.

        Args:
            participant_message: The raw participant message.
            current_state: Current simulation state (unused in base rules,
                available for custom rules).
            conversation_history: Previous messages in this conversation.

        Returns:
            A ``ResponseDirective`` with policy decisions.
        """
        intent = _classify_intent(participant_message)
        msg_lower = participant_message.lower()

        # ── 1. Fact availability ──────────────────────────────────────────
        allowed_facts: list[str] = list(self._stakeholder.knowledge)

        # ── 2. Response category ──────────────────────────────────────────
        if self._check_escalation(msg_lower):
            response_category = "escalate"
        elif intent == MessageIntent.CHALLENGE:
            response_category = "reject"
        elif intent == MessageIntent.PROPOSAL:
            response_category = "approve"
        elif intent == MessageIntent.REQUEST:
            response_category = "request_info"
        elif intent == MessageIntent.QUESTION:
            # Check if the question touches a prohibited topic or false belief
            if self._check_prohibited_topic(participant_message):
                response_category = "deflect"
            else:
                response_category = "request_info"
        else:
            response_category = "deflect"

        # ── 3. Tone selection ─────────────────────────────────────────────
        required_tone = self._select_tone(intent, response_category)

        # ── 4. Prohibited topics ──────────────────────────────────────────
        prohibited_topics = list(self._stakeholder.disclosure_rules)

        # ── 5. Max reveal depth ──────────────────────────────────────────
        max_reveal_depth = self._compute_reveal_depth(intent, response_category)

        # ── 6. Disclosure check ──────────────────────────────────────────
        allowed_facts = self._apply_disclosure_rules(allowed_facts, msg_lower)

        # ── 7. Trust change ──────────────────────────────────────────────
        trust_change = self._compute_trust_change(intent, participant_message, msg_lower)

        # ── 8. Escalation ────────────────────────────────────────────────
        escalate = response_category == "escalate"

        return ResponseDirective(
            allowed_facts=allowed_facts,
            prohibited_topics=prohibited_topics,
            required_tone=required_tone,
            response_category=response_category,
            max_reveal_depth=max_reveal_depth,
            trust_change=trust_change,
            escalate=escalate,
        )

    # ── Internal policy helpers ────────────────────────────────────────────────

    def _check_escalation(self, msg_lower: str) -> bool:
        """Check whether the message triggers any escalation rules."""
        msg_norm = _normalise(msg_lower)
        # Check escalation_rules for trigger patterns
        for rule in self._stakeholder.escalation_rules:
            if _normalise(rule) in msg_norm:
                return True
        # General escalation triggers
        return bool(_ESCALATION_TRIGGERS.search(msg_lower))

    def _check_prohibited_topic(self, message: str) -> bool:
        """Check whether the message touches a false belief or hidden topic."""
        msg_norm = _normalise(message)
        msg_words = set(msg_norm.split())
        for belief in self._stakeholder.false_beliefs:
            belief_norm = _normalise(belief)
            # Try full substring match first
            if belief_norm in msg_norm:
                return True
            # Fall back to significant-word overlap (words with 3+ chars)
            belief_words = {w for w in belief_norm.split() if len(w) >= 3}
            if belief_words and belief_words.intersection(msg_words):
                return True
        for rule in self._stakeholder.disclosure_rules:
            if _normalise(rule) in msg_norm:
                return True
        return any(_normalise(hidden) in msg_norm for hidden in self._stakeholder.hidden_incentives)

    def _select_tone(self, intent: str, response_category: str) -> str:
        """Select the required tone based on context."""
        if response_category == "escalate":
            return "concerned"
        if response_category == "reject":
            return "skeptical"
        if response_category == "approve":
            return "encouraging"
        if response_category == "request_info":
            if intent == MessageIntent.QUESTION:
                return "neutral"
            return "formal"

        # Check false beliefs — if any exist, tone tilts skeptical
        if self._stakeholder.false_beliefs:
            return "skeptical"
        return "neutral"

    def _compute_reveal_depth(self, intent: str, response_category: str) -> int:
        """Determine how much the stakeholder should reveal."""
        if response_category == "escalate":
            return 0
        if response_category == "approve" and intent == MessageIntent.PROPOSAL:
            return 2  # moderate detail for approved proposals
        if intent == MessageIntent.QUESTION:
            return 1  # surface-level detail for questions
        if response_category == "request_info":
            return 1
        return 0

    def _apply_disclosure_rules(self, allowed_facts: list[str], msg_lower: str) -> list[str]:
        """Remove facts whose disclosure rules are violated by the message."""
        msg_norm = _normalise(msg_lower)
        filtered: list[str] = []
        for fact in allowed_facts:
            # If a disclosure rule mentions a topic, check if the
            # participant's message crosses it — simple containment check.
            violated = False
            fact_norm = _normalise(fact)
            for rule in self._stakeholder.disclosure_rules:
                rule_norm = _normalise(rule)
                # If the rule pattern appears in the fact, and the
                # message also touches the rule topic, block the fact.
                if rule_norm in fact_norm and rule_norm in msg_norm:
                    violated = True
                    break
            if not violated:
                filtered.append(fact)
        return filtered

    def _compute_trust_change(self, intent: str, message: str, msg_lower: str) -> float:
        """Calculate trust delta based on participant behaviour.

        Asking relevant questions → +trust.
        Asking about hidden/false topics → -trust.
        """
        change = 0.0
        msg_norm = _normalise(message)

        # Positive signal: asking relevant questions
        if intent == MessageIntent.QUESTION:
            # Check if the question relates to stakeholder knowledge
            for fact in self._stakeholder.knowledge:
                fact_norm = _normalise(fact)
                if fact_norm in msg_norm or any(word in msg_norm for word in fact_norm.split()):
                    change += 0.5
                    break

        # Negative signal: challenging or asking about hidden things
        if intent == MessageIntent.CHALLENGE:
            change -= 1.0

        # Negative signal: touching false beliefs
        for belief in self._stakeholder.false_beliefs:
            if _normalise(belief) in msg_norm:
                change -= 0.5
                break

        # Negative signal: touching hidden incentives
        for hidden in self._stakeholder.hidden_incentives:
            if _normalise(hidden) in msg_norm:
                change -= 0.75
                break

        return change
