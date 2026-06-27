from __future__ import annotations

import pytest
from pydantic import ValidationError

from afcs_case_schema.models import (
    ActionDefinition,
    ActionRegistry,
    BusinessState,
    CaseDefinition,
    CaseMetadata,
    CaseStatus,
    DataSource,
    DifficultyLevel,
    EvaluationConfig,
    EvaluationDimension,
    EvidenceArtifact,
    EvidenceManifest,
    EvidenceType,
    GovernanceState,
    HardConstraint,
    OrganizationalState,
    StakeholderConfig,
    SystemInfo,
    TechnicalState,
    TimelineConfig,
    TimelineEvent,
)


class TestCaseMetadata:
    def test_valid_metadata(self) -> None:
        meta = CaseMetadata(
            case_id="my_case",
            version="1.2.3",
            title="Test",
            domain="testing",
            status=CaseStatus.draft,
            difficulty=DifficultyLevel.intermediate,
        )
        assert meta.case_id == "my_case"
        assert meta.version == "1.2.3"

    def test_invalid_case_id_empty(self) -> None:
        with pytest.raises(ValidationError):
            CaseMetadata(
                case_id="",
                version="1.0.0",
                title="Test",
                domain="testing",
                status=CaseStatus.draft,
                difficulty=DifficultyLevel.introductory,
            )

    def test_invalid_case_id_pattern(self) -> None:
        with pytest.raises(ValidationError):
            CaseMetadata(
                case_id="UpperCase",
                version="1.0.0",
                title="Test",
                domain="testing",
                status=CaseStatus.draft,
                difficulty=DifficultyLevel.introductory,
            )

    def test_invalid_semver(self) -> None:
        with pytest.raises(ValidationError):
            CaseMetadata(
                case_id="my_case",
                version="not-semver",
                title="Test",
                domain="testing",
                status=CaseStatus.draft,
                difficulty=DifficultyLevel.introductory,
            )

    def test_invalid_semver_extra_segment(self) -> None:
        with pytest.raises(ValidationError):
            CaseMetadata(
                case_id="my_case",
                version="1.0.0.0",
                title="Test",
                domain="testing",
                status=CaseStatus.draft,
                difficulty=DifficultyLevel.introductory,
            )

    def test_invalid_semver_non_numeric(self) -> None:
        with pytest.raises(ValidationError):
            CaseMetadata(
                case_id="my_case",
                version="1.a.0",
                title="Test",
                domain="testing",
                status=CaseStatus.draft,
                difficulty=DifficultyLevel.introductory,
            )

    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            CaseMetadata(
                case_id="my_case",
                version="1.0.0",
                title="Test",
                domain="testing",
                status="unknown_status",  # type: ignore[arg-type]
                difficulty=DifficultyLevel.introductory,
            )

    def test_invalid_difficulty(self) -> None:
        with pytest.raises(ValidationError):
            CaseMetadata(
                case_id="my_case",
                version="1.0.0",
                title="Test",
                domain="testing",
                status=CaseStatus.draft,
                difficulty="expert",  # type: ignore[arg-type]
            )

    def test_default_author_reviewer_lists(self) -> None:
        meta = CaseMetadata(
            case_id="my_case",
            version="1.0.0",
            title="Test",
            domain="testing",
            status=CaseStatus.draft,
            difficulty=DifficultyLevel.introductory,
        )
        assert meta.author_ids == []
        assert meta.reviewer_ids == []


class TestBusinessState:
    def test_minimal(self) -> None:
        state = BusinessState(stated_goal="Do something")
        assert state.stated_goal == "Do something"
        assert state.latent_goal is None
        assert state.baseline_metrics == {}
        assert state.success_criteria == []

    def test_full(self) -> None:
        state = BusinessState(
            stated_goal="Do something",
            latent_goal="Do something else",
            baseline_metrics={"uptime": 99.9},
            success_criteria=["Must pass"],
            budget={"amount": 50000, "currency": "USD"},
            deadline_days=30,
            current_process="Manual review",
            business_risks=["Budget overrun"],
        )
        assert state.latent_goal == "Do something else"

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            BusinessState(
                stated_goal="X",
                extra_field="should not exist",  # type: ignore[call-arg]
            )


class TestTechnicalState:
    def test_minimal(self) -> None:
        state = TechnicalState()
        assert state.systems == []
        assert state.data_sources == []

    def test_with_systems(self) -> None:
        sys1 = SystemInfo(name="api", type="backend")
        ds1 = DataSource(name="users_db", type="postgres")
        state = TechnicalState(systems=[sys1], data_sources=[ds1])
        assert len(state.systems) == 1
        assert state.systems[0].name == "api"

    def test_system_frozen(self) -> None:
        sys1 = SystemInfo(name="api", type="backend")
        with pytest.raises(ValidationError):
            sys1.name = "changed"  # type: ignore[misc]


class TestStakeholderConfig:
    def test_minimal(self) -> None:
        s = StakeholderConfig(stakeholder_id="s1", role="Engineer")
        assert s.authority == 0
        assert s.trust_initial == 5

    def test_authority_bounds(self) -> None:
        with pytest.raises(ValidationError):
            StakeholderConfig(stakeholder_id="s1", role="Engineer", authority=11)

        with pytest.raises(ValidationError):
            StakeholderConfig(stakeholder_id="s1", role="Engineer", authority=-1)

    def test_trust_bounds(self) -> None:
        with pytest.raises(ValidationError):
            StakeholderConfig(stakeholder_id="s1", role="Engineer", trust_initial=11)


class TestOrganizationalState:
    def test_empty_stakeholders(self) -> None:
        org = OrganizationalState()
        assert org.stakeholders == []

    def test_with_stakeholders(self) -> None:
        s1 = StakeholderConfig(stakeholder_id="s1", role="Engineer")
        org = OrganizationalState(stakeholders=[s1])
        assert len(org.stakeholders) == 1


class TestGovernanceState:
    def test_minimal(self) -> None:
        g = GovernanceState()
        assert g.data_classification is None
        assert g.applicable_policies == []


class TestTimeline:
    def test_minimal(self) -> None:
        tc = TimelineConfig()
        assert tc.start_day == 0

    def test_scheduled_event(self) -> None:
        event = TimelineEvent(day=5, event_type="audit")
        tc = TimelineConfig(scheduled_events=[event])
        assert tc.scheduled_events[0].day == 5

    def test_event_day_negative(self) -> None:
        with pytest.raises(ValidationError):
            TimelineEvent(day=-1, event_type="bad")


class TestEvidence:
    def test_minimal_artifact(self) -> None:
        art = EvidenceArtifact(
            artifact_id="a1",
            type=EvidenceType.document,
            path="docs/report.md",
        )
        assert not art.visible_initially

    def test_manifest(self) -> None:
        art = EvidenceArtifact(
            artifact_id="a1",
            type=EvidenceType.document,
            path="docs/report.md",
        )
        manifest = EvidenceManifest(artifacts=[art])
        assert len(manifest.artifacts) == 1


class TestActions:
    def test_action_definition_minimal(self) -> None:
        ad = ActionDefinition(action_type="test")
        assert ad.preconditions == []

    def test_action_registry(self) -> None:
        ad = ActionDefinition(action_type="test")
        reg = ActionRegistry(allowed=[ad])
        assert len(reg.allowed) == 1


class TestEvaluation:
    def test_dimension_minimal(self) -> None:
        dim = EvaluationDimension(name="test_dim")
        assert dim.weight == 1.0

    def test_dimension_weight_bounds(self) -> None:
        with pytest.raises(ValidationError):
            EvaluationDimension(name="bad", weight=1.5)

        with pytest.raises(ValidationError):
            EvaluationDimension(name="bad", weight=-0.1)

    def test_hard_constraint(self) -> None:
        hc = HardConstraint(
            constraint_type="must_not_leak",
            condition="no_secrets_in_output",
        )
        assert hc.severity == "major"

    def test_evaluation_config_minimal(self) -> None:
        ec = EvaluationConfig()
        assert ec.dimensions == []


class TestCaseDefinition:
    def test_minimal_valid(self) -> None:
        definition = CaseDefinition(
            metadata=CaseMetadata(
                case_id="my_case",
                version="1.0.0",
                title="Test",
                domain="testing",
                status=CaseStatus.draft,
                difficulty=DifficultyLevel.introductory,
            ),
            business=BusinessState(stated_goal="Do something"),
            technical=TechnicalState(),
            organization=OrganizationalState(),
            governance=GovernanceState(),
            timeline=TimelineConfig(),
            evidence=EvidenceManifest(),
            actions=ActionRegistry(),
            evaluation=EvaluationConfig(),
        )
        assert definition.metadata.case_id == "my_case"

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            CaseDefinition(
                metadata=CaseMetadata(
                    case_id="my_case",
                    version="1.0.0",
                    title="Test",
                    domain="testing",
                    status=CaseStatus.draft,
                    difficulty=DifficultyLevel.introductory,
                ),
                business=BusinessState(stated_goal="Do something"),
                technical=TechnicalState(),
                organization=OrganizationalState(),
                governance=GovernanceState(),
                timeline=TimelineConfig(),
                evidence=EvidenceManifest(),
                actions=ActionRegistry(),
                evaluation=EvaluationConfig(),
                extra_top_level="nope",  # type: ignore[call-arg]
            )


class TestFrozen:
    def test_model_frozen(self) -> None:
        meta = CaseMetadata(
            case_id="my_case",
            version="1.0.0",
            title="Test",
            domain="testing",
            status=CaseStatus.draft,
            difficulty=DifficultyLevel.introductory,
        )
        with pytest.raises(ValidationError):
            meta.case_id = "new_case"  # type: ignore[misc]
