"""Test fixture for case schema tests — a minimal valid CaseDefinition."""

from __future__ import annotations

from afcs_case_schema.models import (
    ActionDefinition,
    ActionRegistry,
    BusinessState,
    CaseDefinition,
    CaseMetadata,
    CaseStatus,
    DifficultyLevel,
    EvaluationConfig,
    EvaluationDimension,
    EvidenceArtifact,
    EvidenceManifest,
    EvidenceType,
    GovernanceState,
    OrganizationalState,
    StakeholderConfig,
    SystemInfo,
    TechnicalState,
    TimelineConfig,
    TimelineEvent,
)


def make_minimal_case_definition(**overrides: object) -> CaseDefinition:
    """Build a minimal valid CaseDefinition.

    Override any field by passing keyword arguments matching the CaseDefinition
    attribute names (nested models are accepted as-is).
    """
    kwargs: dict = {
        "metadata": CaseMetadata(
            case_id="test_fixture_case",
            version="1.0.0",
            title="Test Fixture Case",
            domain="testing",
            status=CaseStatus.draft,
            difficulty=DifficultyLevel.introductory,
        ),
        "business": BusinessState(
            stated_goal="Verify the schema works",
            latent_goal=None,
            baseline_metrics={},
            success_criteria=["Schema validates"],
            budget={"amount": 1000, "currency": "USD"},
            deadline_days=10,
            current_process=None,
            business_risks=[],
        ),
        "technical": TechnicalState(
            systems=[
                SystemInfo(
                    name="app_server",
                    type="web",
                    description="The main application server",
                    constraints=[],
                )
            ],
            data_sources=[],
        ),
        "organization": OrganizationalState(
            stakeholders=[
                StakeholderConfig(
                    stakeholder_id="eng_lead",
                    role="Engineering Lead",
                    authority=8,
                    trust_initial=7,
                )
            ]
        ),
        "governance": GovernanceState(
            data_classification="internal",
            applicable_policies=["data_policy_v2"],
        ),
        "timeline": TimelineConfig(
            start_day=0,
            scheduled_events=[TimelineEvent(day=14, event_type="milestone_review")],
        ),
        "evidence": EvidenceManifest(
            artifacts=[
                EvidenceArtifact(
                    artifact_id="briefing_doc",
                    type=EvidenceType.document,
                    path="docs/briefing.md",
                    visible_initially=True,
                )
            ]
        ),
        "actions": ActionRegistry(
            allowed=[
                ActionDefinition(
                    action_type="gather_requirements",
                    parameter_schema={
                        "type": "object",
                        "properties": {"scope": {"type": "string"}},
                    },
                    preconditions=["phase == discovery"],
                    time_cost=30,
                )
            ]
        ),
        "evaluation": EvaluationConfig(
            dimensions=[
                EvaluationDimension(
                    name="discovery",
                    weight=0.5,
                    criteria=["Identified the problem correctly"],
                )
            ],
            hard_constraints=[],
        ),
    }
    kwargs.update(overrides)
    return CaseDefinition(**kwargs)
