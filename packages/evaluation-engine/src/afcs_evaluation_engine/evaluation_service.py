from __future__ import annotations

from afcs_case_schema.models import CaseDefinition
from afcs_domain.events import SimulationEvent
from afcs_domain.state import CanonicalState
from pydantic import BaseModel, Field

from .hard_constraints import ConstraintViolation, build_default_constraints, check_hard_constraints
from .report_service import ParticipantReport, ReportService
from .scoring import DimensionScore, compute_dimension_scores, compute_overall_score
from .validator_registry import ValidatorRegistry
from .validators import ValidatorResult, build_default_validators


class EvaluationResult(BaseModel):
    """Complete result of a session evaluation."""

    session_id: str
    case_id: str
    overall_score: float
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    validator_results: list[ValidatorResult] = Field(default_factory=list)
    hard_constraint_violations: list[ConstraintViolation] = Field(default_factory=list)
    report: ParticipantReport | None = None

    model_config = {"extra": "forbid", "frozen": True}


class EvaluationService:
    """Orchestrates the full evaluation of a simulation session."""

    def __init__(
        self,
        validator_registry: ValidatorRegistry | None = None,
    ) -> None:
        self._registry = validator_registry or self._default_registry()
        self._report_service = ReportService()

    @staticmethod
    def _default_registry() -> ValidatorRegistry:
        """Create a ValidatorRegistry with all default validators."""
        registry = ValidatorRegistry()
        registry.register_many(build_default_validators())
        return registry

    @property
    def registry(self) -> ValidatorRegistry:
        return self._registry

    def evaluate_session(
        self,
        session_id: str,
        session_events: list[SimulationEvent],
        final_state: CanonicalState,
        case_definition: CaseDefinition,
        human_scores: dict[str, float] | None = None,
    ) -> EvaluationResult:
        """Run the full evaluation pipeline and return results."""
        # 1. Run validators
        validator_results = self._registry.run_all(session_events, final_state, case_definition)

        # 2. Check hard constraints
        constraints = build_default_constraints()
        violations = check_hard_constraints(
            constraints, session_events, final_state, case_definition
        )

        # 3. Compute dimension scores
        dimension_scores = self.get_dimension_scores(
            validator_results, case_definition, human_scores=human_scores
        )

        # 4. Compute overall score
        overall_score = compute_overall_score(dimension_scores)

        # 5. Generate report
        report = self._report_service.generate_report(
            session_id=session_id,
            case_definition=case_definition,
            dimension_scores=dimension_scores,
            hard_constraint_outcomes=violations,
            events=session_events,
            final_state=final_state,
        )

        return EvaluationResult(
            session_id=session_id,
            case_id=case_definition.metadata.case_id,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            validator_results=validator_results,
            hard_constraint_violations=violations,
            report=report,
        )

    def get_dimension_scores(
        self,
        validator_results: list[ValidatorResult],
        case_definition: CaseDefinition,
        dimension_weights: dict[str, float] | None = None,
        human_scores: dict[str, float] | None = None,
    ) -> list[DimensionScore]:
        """Compute dimension scores from validator results."""
        return compute_dimension_scores(
            validator_results=validator_results,
            case_definition=case_definition,
            dimension_weights=dimension_weights,
            human_scores=human_scores,
        )

    @staticmethod
    def adjudicate(machine_score: float, human_score: float | None) -> float:
        """Adjudicate between machine and human scores.

        Returns:
            Weighted blend: 0.7 * machine + 0.3 * human,
            or machine_score if human_score is None.
        """
        if human_score is not None:
            return 0.7 * machine_score + 0.3 * human_score
        return machine_score
