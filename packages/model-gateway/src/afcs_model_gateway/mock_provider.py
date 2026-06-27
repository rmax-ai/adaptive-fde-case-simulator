from __future__ import annotations

import re
from typing import Any, ClassVar

from pydantic import BaseModel

from afcs_model_gateway.provider import ModelResponse


class MockProvider:
    """A deterministic mock LLM provider for local development and testing.

    Returns canned responses based on pattern matching against the
    response_category derived from a policy directive.  The caller passes
    category hints via metadata or the system prompt.
    """

    def __init__(self, model: str = "mock-model") -> None:
        self._model = model
        self._call_count = 0
        self._last_system_prompt: str = ""
        self._last_messages: list[dict] = []

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def last_system_prompt(self) -> str:
        return self._last_system_prompt

    @property
    def last_messages(self) -> list[dict]:
        return list(self._last_messages)

    # ── canned response table ────────────────────────────────────────────────
    _CANNED: ClassVar[dict[str, str]] = {
        "approve": "I think that's a reasonable approach. Let's proceed.",
        "reject": "I'm not comfortable with that direction. We need to reconsider.",
        "request_info": "Can you tell me more about your thinking on this?",
        "escalate": "This requires higher-level approval. I'll need to escalate this decision.",
        "deflect": "Let's stay focused on the current priorities for now.",
    }

    async def generate(
        self,
        *,
        system_prompt: str,
        messages: list[dict],
        response_schema: type[BaseModel] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModelResponse:
        self._call_count += 1
        self._last_system_prompt = system_prompt
        self._last_messages = list(messages)

        # Determine the category from metadata or fall back to extraction
        category = "deflect"
        if metadata and "response_category" in metadata:
            category = metadata["response_category"]
        else:
            # Simple heuristic: look for keywords in system prompt
            for key in self._CANNED:
                if key in system_prompt.lower():
                    category = key
                    break

        content = self._CANNED.get(category, self._CANNED["deflect"])

        # Persona-aware fallback when no specific category matched
        if (
            category == "deflect"
            and content == self._CANNED["deflect"]
            and "persona" in system_prompt.lower()
        ):
            # Extract the role from the system prompt (e.g. "You are the CTO" → "CTO")
            role_match = re.search(
                r"(?:You are(?: the)?|as the)\s+(\w+)", system_prompt, re.IGNORECASE
            )
            if role_match:
                role = role_match.group(1).strip().upper()
                content = (
                    f"As the {role}, I'd like to hear more about your proposal before committing."
                )
            else:
                # Fallback to role-word matching
                lines = system_prompt.split("\n")
                for line in lines:
                    line_lower = line.lower().strip()
                    for role_word in [
                        "cto",
                        "cfo",
                        "product manager",
                        "engineer",
                        "director",
                    ]:
                        if role_word in line_lower:
                            display = role_word.title()
                            content = (
                                f"As the {display}, I'd like to hear more about"
                                " your proposal before committing."
                            )
                            break
                    if content != self._CANNED["deflect"]:
                        break

        return ModelResponse(
            content=content,
            token_usage={"prompt_tokens": 50, "completion_tokens": 20},
            model=self._model,
            provider="mock",
        )
