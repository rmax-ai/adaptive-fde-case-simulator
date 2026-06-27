from __future__ import annotations

import pytest
from afcs_model_gateway import LanguageModelProvider, ModelProviderRegistry
from afcs_model_gateway.mock_provider import MockProvider
from afcs_model_gateway.provider import ModelResponse

# ── Tests: MockProvider ──────────────────────────────────────────────────────


class TestMockProvider:
    @pytest.mark.asyncio
    async def test_approve_response(self) -> None:
        provider = MockProvider()
        resp = await provider.generate(
            system_prompt="You are a helpful assistant.",
            messages=[{"role": "user", "content": "I think we should proceed."}],
            metadata={"response_category": "approve"},
        )
        assert resp.content == "I think that's a reasonable approach. Let's proceed."
        assert resp.provider == "mock"
        assert resp.model == "mock-model"
        assert resp.token_usage["prompt_tokens"] == 50
        assert resp.token_usage["completion_tokens"] == 20

    @pytest.mark.asyncio
    async def test_reject_response(self) -> None:
        provider = MockProvider()
        resp = await provider.generate(
            system_prompt="You are a helpful assistant.",
            messages=[],
            metadata={"response_category": "reject"},
        )
        assert resp.content == "I'm not comfortable with that direction. We need to reconsider."

    @pytest.mark.asyncio
    async def test_request_info_response(self) -> None:
        provider = MockProvider()
        resp = await provider.generate(
            system_prompt="You are a helpful assistant.",
            messages=[],
            metadata={"response_category": "request_info"},
        )
        assert resp.content == "Can you tell me more about your thinking on this?"

    @pytest.mark.asyncio
    async def test_escalate_response(self) -> None:
        provider = MockProvider()
        resp = await provider.generate(
            system_prompt="You need to make a decision.",
            messages=[],
            metadata={"response_category": "escalate"},
        )
        assert (
            resp.content
            == "This requires higher-level approval. I'll need to escalate this decision."
        )

    @pytest.mark.asyncio
    async def test_deflect_response(self) -> None:
        provider = MockProvider()
        resp = await provider.generate(
            system_prompt="Be cautious.",
            messages=[],
            metadata={"response_category": "deflect"},
        )
        assert resp.content == "Let's stay focused on the current priorities for now."

    @pytest.mark.asyncio
    async def test_default_fallback_without_metadata(self) -> None:
        provider = MockProvider()
        resp = await provider.generate(
            system_prompt="Just respond naturally.",
            messages=[],
        )
        # Falls back to "deflect"
        assert resp.content == "Let's stay focused on the current priorities for now."

    @pytest.mark.asyncio
    async def test_persona_aware_fallback(self) -> None:
        """When no category matches but persona is in system prompt, use persona-aware response."""
        provider = MockProvider()
        resp = await provider.generate(
            system_prompt=(
                "You are the CTO of a company and this is your persona. Respond as the CTO."
            ),
            messages=[],
        )
        # "deflect" is the fallback category, but persona overrides it
        assert "CTO" in resp.content

    @pytest.mark.asyncio
    async def test_call_count(self) -> None:
        provider = MockProvider()
        assert provider.call_count == 0
        await provider.generate(
            system_prompt="Hi.",
            messages=[],
            metadata={"response_category": "approve"},
        )
        assert provider.call_count == 1
        await provider.generate(
            system_prompt="Hi again.",
            messages=[],
            metadata={"response_category": "reject"},
        )
        assert provider.call_count == 2

    @pytest.mark.asyncio
    async def test_implements_protocol(self) -> None:
        """MockProvider should satisfy the LanguageModelProvider protocol."""
        provider = MockProvider()
        assert isinstance(provider, LanguageModelProvider)


# ── Tests: ModelResponse ─────────────────────────────────────────────────────


class TestModelResponse:
    def test_default_values(self) -> None:
        resp = ModelResponse(content="Hello!")
        assert resp.content == "Hello!"
        assert resp.token_usage == {"prompt_tokens": 0, "completion_tokens": 0}
        assert resp.model == ""
        assert resp.provider == ""

    def test_custom_values(self) -> None:
        resp = ModelResponse(
            content="Hello!",
            token_usage={"prompt_tokens": 100, "completion_tokens": 50},
            model="gpt-4",
            provider="openai",
        )
        assert resp.token_usage["prompt_tokens"] == 100
        assert resp.model == "gpt-4"
        assert resp.provider == "openai"


# ── Tests: ModelProviderRegistry ─────────────────────────────────────────────


class TestModelProviderRegistry:
    def test_register_and_get(self) -> None:
        registry = ModelProviderRegistry()
        provider = MockProvider()
        registry.register("mock", provider)
        retrieved = registry.get("mock")
        assert retrieved is provider

    def test_get_unknown_raises_key_error(self) -> None:
        registry = ModelProviderRegistry()
        with pytest.raises(KeyError, match="No provider registered under 'unknown'"):
            registry.get("unknown")

    def test_register_duplicate_raises_value_error(self) -> None:
        registry = ModelProviderRegistry()
        registry.register("mock", MockProvider())
        with pytest.raises(ValueError, match="Provider 'mock' is already registered"):
            registry.register("mock", MockProvider())

    def test_multiple_providers(self) -> None:
        registry = ModelProviderRegistry()
        mock1 = MockProvider()
        mock2 = MockProvider(model="other-model")
        registry.register("primary", mock1)
        registry.register("secondary", mock2)
        assert registry.get("primary") is mock1
        assert registry.get("secondary") is mock2

    def test_registered_names(self) -> None:
        registry = ModelProviderRegistry()
        assert registry.registered_names == []
        registry.register("a", MockProvider())
        registry.register("b", MockProvider())
        assert "a" in registry.registered_names
        assert "b" in registry.registered_names
