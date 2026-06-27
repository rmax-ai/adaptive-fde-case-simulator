from __future__ import annotations

import pytest
from afcs_case_schema.models import CaseDefinition, StakeholderConfig
from afcs_stakeholder_engine.policy_engine import StakeholderPolicyEngine

# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def cto_config() -> StakeholderConfig:
    return StakeholderConfig(
        stakeholder_id="cto",
        role="CTO",
        trust_initial=5,
        authority=7,
        goals=["Improve platform reliability", "Reduce technical debt"],
        hidden_incentives=["impending layoffs"],
        knowledge=[
            "system_architecture_overview",
            "current_incident_status",
            "team_capacity_report",
        ],
        false_beliefs=[
            "third_party_api_is_stable",
        ],
        disclosure_rules=[
            "do_not_disclose_pending_layoffs",
        ],
        escalation_rules=[
            "security_incident",
        ],
    )


@pytest.fixture
def case_def(cto_config: StakeholderConfig) -> CaseDefinition:
    # Minimal case definition — only the fields required for construction
    from afcs_case_schema.models import (
        ActionRegistry,
        BusinessState,
        CaseMetadata,
        CaseStatus,
        DifficultyLevel,
        EvaluationConfig,
        EvidenceManifest,
        GovernanceState,
        OrganizationalState,
        TechnicalState,
        TimelineConfig,
    )

    return CaseDefinition(
        metadata=CaseMetadata(
            case_id="test_case",
            version="1.0.0",
            title="Test Case",
            domain="test",
            status=CaseStatus.draft,
            difficulty=DifficultyLevel.intermediate,
        ),
        business=BusinessState(stated_goal="Test the policy engine"),
        technical=TechnicalState(),
        organization=OrganizationalState(stakeholders=[cto_config]),
        governance=GovernanceState(),
        timeline=TimelineConfig(),
        evidence=EvidenceManifest(),
        actions=ActionRegistry(),
        evaluation=EvaluationConfig(),
    )


@pytest.fixture
def engine(cto_config: StakeholderConfig, case_def: CaseDefinition) -> StakeholderPolicyEngine:
    return StakeholderPolicyEngine(stakeholder_config=cto_config, case_definition=case_def)


# ── Tests: Fact Availability ─────────────────────────────────────────────────


class TestFactAvailability:
    def test_knowledge_facts_available(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="What's the current status of the incident?",
            current_state={},
            conversation_history=[],
        )
        assert "current_incident_status" in directive.allowed_facts
        assert "system_architecture_overview" in directive.allowed_facts
        assert "team_capacity_report" in directive.allowed_facts

    def test_false_belief_not_in_allowed_facts(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="Is the third party API stable?",
            current_state={},
            conversation_history=[],
        )
        # False beliefs are NOT facts — they shouldn't appear in allowed_facts
        assert "third_party_api_is_stable" not in directive.allowed_facts


# ── Tests: Disclosure Rules ──────────────────────────────────────────────────


class TestDisclosureRules:
    def test_disclosure_rule_filters_fact(self, engine: StakeholderPolicyEngine) -> None:
        """If a disclosure rule mentions a topic the participant is asking about,
        facts related to that rule are filtered out."""
        # The stakeholder has rule "do_not_disclose_pending_layoffs"
        # and has hidden incentives about layoffs. Asking about layoffs
        # should block related facts (there are no facts about layoffs in
        # knowledge, but the mechanism should work).
        directive = engine.evaluate(
            participant_message="Are there any layoffs planned?",
            current_state={},
            conversation_history=[],
        )
        # The disclosure rule "do_not_disclose_pending_layoffs" doesn't match
        # any fact name, so no facts get filtered — but the prohibited_topics
        # list should contain the rule
        assert "do_not_disclose_pending_layoffs" in directive.prohibited_topics


# ── Tests: Escalation Rules ──────────────────────────────────────────────────


class TestEscalation:
    def test_escalation_triggered_by_rule_keyword(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="We have a security incident on our hands.",
            current_state={},
            conversation_history=[],
        )
        assert directive.escalate is True
        assert directive.response_category == "escalate"

    def test_escalation_triggered_by_general_keyword(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="I'm filing a formal complaint about this process.",
            current_state={},
            conversation_history=[],
        )
        assert directive.escalate is True
        assert directive.response_category == "escalate"


# ── Tests: Trust Changes ─────────────────────────────────────────────────────


class TestTrustChanges:
    def test_relevant_question_increases_trust(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="Can you tell me about the current incident status?",
            current_state={},
            conversation_history=[],
        )
        # "current_incident_status" is in knowledge — the word "incident" also matches
        assert directive.trust_change > 0

    def test_challenge_decreases_trust(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="I disagree with that assessment entirely.",
            current_state={},
            conversation_history=[],
        )
        assert directive.trust_change == -1.0

    def test_false_belief_touch_decreases_trust(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="I think the third party API is stable enough.",
            current_state={},
            conversation_history=[],
        )
        assert directive.trust_change < 0

    def test_hidden_incentive_touch_decreases_trust_more(
        self, engine: StakeholderPolicyEngine
    ) -> None:
        directive = engine.evaluate(
            participant_message="Are there impending layoffs I should know about?",
            current_state={},
            conversation_history=[],
        )
        assert directive.trust_change == -0.75


# ── Tests: Response Category Classification ──────────────────────────────────


class TestResponseCategory:
    def test_proposal_gets_approve(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="I propose we refactor the monitoring stack first.",
            current_state={},
            conversation_history=[],
        )
        assert directive.response_category == "approve"

    def test_challenge_gets_reject(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="That approach is fundamentally wrong.",
            current_state={},
            conversation_history=[],
        )
        assert directive.response_category == "reject"

    def test_greeting_gets_deflect(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="Hello, nice to meet you.",
            current_state={},
            conversation_history=[],
        )
        assert directive.response_category == "deflect"

    def test_question_about_false_belief_gets_deflect(
        self, engine: StakeholderPolicyEngine
    ) -> None:
        directive = engine.evaluate(
            participant_message="Is the third party API actually stable?",
            current_state={},
            conversation_history=[],
        )
        # A question touching a false belief gets deflected
        assert directive.response_category == "deflect"


# ── Tests: Tone Selection ────────────────────────────────────────────────────


class TestToneSelection:
    def test_escalation_is_concerned(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="This is a security incident.",
            current_state={},
            conversation_history=[],
        )
        assert directive.required_tone == "concerned"

    def test_reject_is_skeptical(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="I disagree with your proposal.",
            current_state={},
            conversation_history=[],
        )
        assert directive.required_tone == "skeptical"

    def test_approve_is_encouraging(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="I suggest we increase monitoring coverage.",
            current_state={},
            conversation_history=[],
        )
        assert directive.required_tone == "encouraging"


# ── Tests: Reveal Depth ──────────────────────────────────────────────────────


class TestRevealDepth:
    def test_escalation_no_reveal(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="This is a security incident.",
            current_state={},
            conversation_history=[],
        )
        assert directive.max_reveal_depth == 0

    def test_approved_proposal_moderate_reveal(self, engine: StakeholderPolicyEngine) -> None:
        directive = engine.evaluate(
            participant_message="I propose we roll out the new deployment strategy.",
            current_state={},
            conversation_history=[],
        )
        assert directive.max_reveal_depth == 2
