from __future__ import annotations

import uuid
from typing import Any

from afcs_case_schema.models import StakeholderConfig
from afcs_model_gateway.provider import LanguageModelProvider

from afcs_stakeholder_engine.models import ResponseDirective, StakeholderResponse


class StakeholderLanguageRenderer:
    """Renders a ``ResponseDirective`` into natural-language stakeholder dialogue
    using an LLM *provider* (or a mock for testing).

    The renderer:
    1. Builds a system prompt from the stakeholder persona + directive constraints.
    2. Calls the LLM provider.
    3. Validates that disclosed facts are a subset of allowed facts.
    4. Returns a ``StakeholderResponse``.
    """

    def __init__(self, model_provider: LanguageModelProvider) -> None:
        self._provider = model_provider

    @property
    def provider(self) -> LanguageModelProvider:
        return self._provider

    async def render(
        self,
        stakeholder_config: StakeholderConfig,
        directive: ResponseDirective,
        participant_message: str,
        conversation_history: list[dict[str, Any]],
    ) -> StakeholderResponse:
        """Render a natural-language stakeholder response.

        Args:
            stakeholder_config: The stakeholder's configuration (persona, etc.).
            directive: The policy directive constraining the response.
            participant_message: The participant's last message.
            conversation_history: Prior conversation turns.

        Returns:
            A ``StakeholderResponse`` with the rendered message.
        """
        system_prompt = self._build_system_prompt(stakeholder_config, directive)
        messages = self._build_messages(conversation_history, participant_message)

        # Build metadata with the directive for the provider
        metadata: dict[str, Any] = {
            "response_category": directive.response_category,
            "required_tone": directive.required_tone,
        }

        model_response = await self._provider.generate(
            system_prompt=system_prompt,
            messages=messages,
            metadata=metadata,
        )

        # Validate that disclosed facts are allowed
        disclosed = self._extract_fact_ids(model_response.content, directive)

        return StakeholderResponse(
            message=model_response.content,
            disclosed_fact_ids=disclosed,
            tone=directive.required_tone,
            policy_decision_id=str(uuid.uuid4()),
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_system_prompt(
        self, stakeholder: StakeholderConfig, directive: ResponseDirective
    ) -> str:
        """Build the system prompt that shapes the LLM's persona and constraints."""
        parts: list[str] = [
            f"You are {stakeholder.role} (ID: {stakeholder.stakeholder_id}).",
            "",
            "## Persona",
            f"Role: {stakeholder.role}",
            f"Goals: {'; '.join(stakeholder.goals) if stakeholder.goals else 'None specified.'}",
            "",
            "## Response Constraints",
            f"Required tone: {directive.required_tone}",
            f"Response category: {directive.response_category}",
            f"Max reveal depth: {directive.max_reveal_depth}",
            f"Escalate: {directive.escalate}",
            "",
        ]

        if directive.allowed_facts:
            parts.append("## Allowed Facts (you may reference these)")
            for fact in directive.allowed_facts:
                parts.append(f"- {fact}")
            parts.append("")

        if directive.prohibited_topics:
            parts.append("## Prohibited Topics (do NOT discuss)")
            for topic in directive.prohibited_topics:
                parts.append(f"- {topic}")
            parts.append("")

        parts.append("Respond naturally as this stakeholder, following all constraints above.")

        return "\n".join(parts)

    def _build_messages(
        self,
        conversation_history: list[dict[str, Any]],
        participant_message: str,
    ) -> list[dict[str, str]]:
        """Build the message list for the LLM call."""
        messages: list[dict[str, str]] = []
        for turn in conversation_history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            messages.append({"role": role, "content": str(content)})
        messages.append({"role": "user", "content": participant_message})
        return messages

    def _extract_fact_ids(self, content: str, directive: ResponseDirective) -> list[str]:
        """Extract and validate fact IDs from the generated content.

        For the mock case, we simply check which allowed facts appear
        in the generated content.
        """
        disclosed: list[str] = []
        content_lower = content.lower()
        for fact in directive.allowed_facts:
            if fact.lower() in content_lower:
                disclosed.append(fact)
        return disclosed
