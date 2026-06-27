from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class ModelResponse(BaseModel):
    """Standardised response from any LLM provider."""

    content: str
    token_usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
    model: str = ""
    provider: str = ""


@runtime_checkable
class LanguageModelProvider(Protocol):
    """Protocol for a provider-neutral LLM interface.

    Any concrete provider must implement this protocol to be compatible
    with the AFCS rendering pipeline.
    """

    async def generate(
        self,
        *,
        system_prompt: str,
        messages: list[dict],  # [{"role": "user"|"assistant", "content": "..."}]
        response_schema: type[BaseModel] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModelResponse: ...
