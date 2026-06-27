from __future__ import annotations

import pytest
from afcs_case_schema.models import StakeholderConfig
from afcs_model_gateway import MockProvider
from afcs_stakeholder_engine import ResponseDirective
from afcs_stakeholder_engine.language_renderer import StakeholderLanguageRenderer


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider(model="test-mock")


@pytest.fixture
def renderer(mock_provider: MockProvider) -> StakeholderLanguageRenderer:
    return StakeholderLanguageRenderer(model_provider=mock_provider)


@pytest.fixture
def stakeholder() -> StakeholderConfig:
    return StakeholderConfig(
        stakeholder_id="cto",
        role="CTO",
        trust_initial=5,
        goals=["Improve reliability"],
        knowledge=["current_status", "team_capacity"],
        false_beliefs=[],
        disclosure_rules=[],
        escalation_rules=[],
    )


@pytest.fixture
def approve_directive() -> ResponseDirective:
    return ResponseDirective(
        allowed_facts=["current_status"],
        required_tone="encouraging",
        response_category="approve",
        max_reveal_depth=2,
        trust_change=0.5,
        escalate=False,
    )


@pytest.fixture
def reject_directive() -> ResponseDirective:
    return ResponseDirective(
        allowed_facts=[],
        required_tone="skeptical",
        response_category="reject",
        max_reveal_depth=0,
        trust_change=-1.0,
        escalate=False,
    )


# ── Tests: Basic Rendering ───────────────────────────────────────────────────


class TestBasicRendering:
    @pytest.mark.asyncio
    async def test_render_approve_directive(
        self,
        renderer: StakeholderLanguageRenderer,
        stakeholder: StakeholderConfig,
        approve_directive: ResponseDirective,
    ) -> None:
        response = await renderer.render(
            stakeholder_config=stakeholder,
            directive=approve_directive,
            participant_message="I suggest we improve our monitoring.",
            conversation_history=[],
        )
        assert response.message == "I think that's a reasonable approach. Let's proceed."
        assert response.tone == "encouraging"
        assert response.policy_decision_id != ""

    @pytest.mark.asyncio
    async def test_render_reject_directive(
        self,
        renderer: StakeholderLanguageRenderer,
        stakeholder: StakeholderConfig,
        reject_directive: ResponseDirective,
    ) -> None:
        response = await renderer.render(
            stakeholder_config=stakeholder,
            directive=reject_directive,
            participant_message="I disagree with this plan.",
            conversation_history=[],
        )
        assert response.message == "I'm not comfortable with that direction. We need to reconsider."
        assert response.tone == "skeptical"


# ── Tests: Response Validation (Disclosed Facts ⊆ Allowed Facts) ────────────


class TestFactValidation:
    @pytest.mark.asyncio
    async def test_disclosed_facts_subset_of_allowed(
        self,
        renderer: StakeholderLanguageRenderer,
        stakeholder: StakeholderConfig,
    ) -> None:
        """Disclosed facts should be a subset of allowed facts."""
        directive = ResponseDirective(
            allowed_facts=["current_status", "team_capacity"],
            required_tone="neutral",
            response_category="request_info",
            max_reveal_depth=1,
            trust_change=0.0,
            escalate=False,
        )
        response = await renderer.render(
            stakeholder_config=stakeholder,
            directive=directive,
            participant_message="What's going on?",
            conversation_history=[],
        )
        # The mock returns a canned response that won't mention any facts
        assert len(response.disclosed_fact_ids) == 0

    @pytest.mark.asyncio
    async def test_disclosed_facts_available_when_mentioned(
        self,
        renderer: StakeholderLanguageRenderer,
        stakeholder: StakeholderConfig,
    ) -> None:
        """When the response contains the fact text, it should appear."""
        # Use a directive where the mock response might pick up on the fact
        directive = ResponseDirective(
            allowed_facts=["reasonable approach", "proceed"],
            required_tone="encouraging",
            response_category="approve",
            max_reveal_depth=2,
            trust_change=0.5,
            escalate=False,
        )
        response = await renderer.render(
            stakeholder_config=stakeholder,
            directive=directive,
            participant_message="I suggest we improve our monitoring.",
            conversation_history=[],
        )
        # "reasonable approach" and "proceed" are both in the mock's "approve" response
        assert (
            "reasonable approach" in response.disclosed_fact_ids
            or "proceed" in response.disclosed_fact_ids
        )


# ── Tests: System Prompt Building ────────────────────────────────────────────


class TestSystemPrompt:
    @pytest.mark.asyncio
    async def test_system_prompt_contains_persona(
        self,
        mock_provider: MockProvider,
        renderer: StakeholderLanguageRenderer,
        stakeholder: StakeholderConfig,
        approve_directive: ResponseDirective,
    ) -> None:
        await renderer.render(
            stakeholder_config=stakeholder,
            directive=approve_directive,
            participant_message="Let's proceed with the plan.",
            conversation_history=[],
        )
        assert mock_provider.last_system_prompt is not None
        assert "CTO" in mock_provider.last_system_prompt
        assert "encouraging" in mock_provider.last_system_prompt
        assert "approve" in mock_provider.last_system_prompt

    @pytest.mark.asyncio
    async def test_system_prompt_includes_allowed_facts(
        self,
        mock_provider: MockProvider,
        renderer: StakeholderLanguageRenderer,
        stakeholder: StakeholderConfig,
    ) -> None:
        directive = ResponseDirective(
            allowed_facts=["current_status", "team_capacity"],
            required_tone="neutral",
            response_category="request_info",
            max_reveal_depth=1,
            trust_change=0.0,
            escalate=False,
        )
        await renderer.render(
            stakeholder_config=stakeholder,
            directive=directive,
            participant_message="What is the status?",
            conversation_history=[],
        )
        assert "current_status" in mock_provider.last_system_prompt
        assert "team_capacity" in mock_provider.last_system_prompt

    @pytest.mark.asyncio
    async def test_system_prompt_includes_prohibited_topics(
        self,
        mock_provider: MockProvider,
        renderer: StakeholderLanguageRenderer,
        stakeholder: StakeholderConfig,
    ) -> None:
        directive = ResponseDirective(
            allowed_facts=[],
            prohibited_topics=["layoffs", "security breach"],
            required_tone="neutral",
            response_category="deflect",
            max_reveal_depth=0,
            trust_change=0.0,
            escalate=False,
        )
        await renderer.render(
            stakeholder_config=stakeholder,
            directive=directive,
            participant_message="Hello.",
            conversation_history=[],
        )
        assert "Prohibited Topics" in mock_provider.last_system_prompt
        assert "layoffs" in mock_provider.last_system_prompt
        assert "security breach" in mock_provider.last_system_prompt


# ── Tests: Conversation History ──────────────────────────────────────────────


class TestConversationHistory:
    @pytest.mark.asyncio
    async def test_messages_include_history(
        self,
        mock_provider: MockProvider,
        renderer: StakeholderLanguageRenderer,
        stakeholder: StakeholderConfig,
        approve_directive: ResponseDirective,
    ) -> None:
        history = [
            {"role": "user", "content": "Hello."},
            {"role": "assistant", "content": "How can I help you today?"},
        ]
        await renderer.render(
            stakeholder_config=stakeholder,
            directive=approve_directive,
            participant_message="Let's proceed with the plan.",
            conversation_history=history,
        )
        messages = mock_provider.last_messages
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello."
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "Let's proceed with the plan."
