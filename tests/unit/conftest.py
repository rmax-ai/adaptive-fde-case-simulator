"""Shared fixtures for simulation-engine unit tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from afcs_case_schema import (
    ActionDefinition,
    ActionRegistry as CaseActionRegistry,
    BusinessState,
    CaseDefinition,
    CaseMetadata,
    CaseStatus,
    DifficultyLevel,
    EvaluationConfig,
    EvidenceManifest,
    GovernanceState,
    OrganizationalState,
    StakeholderConfig,
    TechnicalState,
    TimelineConfig,
)
from afcs_domain import SessionStatus, SimulationSession

from afcs_simulation_engine import ActionRegistry, StateTransitionEngine


@pytest.fixture
def sample_case() -> CaseDefinition:
    """A minimal, valid CaseDefinition for testing."""
    return CaseDefinition(
        metadata=CaseMetadata(
            case_id="test_case",
            version="1.0.0",
            title="Test Case",
            domain="test",
            status=CaseStatus.draft,
            difficulty=DifficultyLevel.intermediate,
        ),
        business=BusinessState(
            stated_goal="Test the simulation engine",
            budget={"amount": 50000, "currency": "USD"},
        ),
        technical=TechnicalState(),
        organization=OrganizationalState(
            stakeholders=[
                StakeholderConfig(
                    stakeholder_id="cto",
                    role="CTO",
                    trust_initial=5,
                ),
                StakeholderConfig(
                    stakeholder_id="pm",
                    role="Product Manager",
                    trust_initial=4,
                ),
            ],
        ),
        governance=GovernanceState(),
        timeline=TimelineConfig(),
        evidence=EvidenceManifest(),
        actions=CaseActionRegistry(
            allowed=[
                ActionDefinition(action_type="inspect_artifact"),
                ActionDefinition(action_type="ask_stakeholder"),
                ActionDefinition(action_type="register_assumption"),
                ActionDefinition(action_type="register_risk"),
            ],
        ),
        evaluation=EvaluationConfig(),
    )


@pytest.fixture
def action_registry() -> ActionRegistry:
    """An ActionRegistry pre-populated with all built-in handlers."""
    reg = ActionRegistry()
    reg.register_from_builtins()
    return reg


@pytest.fixture
def engine(sample_case: CaseDefinition, action_registry: ActionRegistry) -> StateTransitionEngine:
    """A StateTransitionEngine wired to the sample case and built-in actions."""
    return StateTransitionEngine(case=sample_case, action_registry=action_registry)


@pytest.fixture
def session_in_progress(engine: StateTransitionEngine) -> SimulationSession:
    """A SimulationSession initialised to IN_PROGRESS with initial state."""
    session = SimulationSession(
        id=uuid4(),
        case_id=engine.case.metadata.case_id,
        case_version=engine.case.metadata.version,
    )
    engine.initialise_session(session)
    return session
