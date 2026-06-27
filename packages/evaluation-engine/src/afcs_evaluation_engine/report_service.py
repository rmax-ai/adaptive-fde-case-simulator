from __future__ import annotations

from datetime import UTC, datetime

from afcs_case_schema.models import CaseDefinition
from afcs_domain.events import SimulationEvent
from afcs_domain.state import CanonicalState
from pydantic import BaseModel, Field

from .hard_constraints import ConstraintViolation
from .scoring import DimensionScore


class ParticipantReport(BaseModel):
    """Full evaluation report for a participant session."""

    session_id: str
    case_id: str
    overall_score: float = Field(ge=0.0, le=1.0)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    hard_constraint_outcomes: list[ConstraintViolation] = Field(default_factory=list)
    strongest_behaviors: list[str] = Field(default_factory=list)
    weakest_behaviors: list[str] = Field(default_factory=list)
    missed_evidence: list[str] = Field(default_factory=list)
    unnecessary_actions: list[str] = Field(default_factory=list)
    critical_decision_points: list[str] = Field(default_factory=list)
    assumption_revisions: int = 0
    governance_decisions: list[str] = Field(default_factory=list)
    alternative_valid_trajectory: str = ""
    counterfactual_improvement: str = ""
    evaluator_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    model_config = {"extra": "forbid", "frozen": True}


class ReportService:
    """Service that assembles a ParticipantReport from evaluation results."""

    def generate_report(
        self,
        session_id: str,
        case_definition: CaseDefinition,
        dimension_scores: list[DimensionScore],
        hard_constraint_outcomes: list[ConstraintViolation],
        events: list[SimulationEvent],
        final_state: CanonicalState,
    ) -> ParticipantReport:
        """Generate a full ParticipantReport from evaluation data.

        The report includes synthesized qualitative observations derived
        from the evaluation results.
        """
        overall_score = self._compute_overall(dimension_scores)
        strongest, weakest = self._identify_strengths_weaknesses(dimension_scores)
        missed = self._find_missed_evidence(dimension_scores)
        unnecessary = self._find_unnecessary_actions(events)
        decision_points = self._identify_critical_decisions(events)
        assumption_revisions = self._count_assumption_revisions(events)
        governance_decisions_list = self._extract_governance_decisions(events)
        alt_trajectory = self._generate_alternative_trajectory(dimension_scores, case_definition)
        counterfactual = self._generate_counterfactual(dimension_scores, case_definition)
        confidence = self._compute_evaluator_confidence(dimension_scores)

        return ParticipantReport(
            session_id=session_id,
            case_id=case_definition.metadata.case_id,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            hard_constraint_outcomes=hard_constraint_outcomes,
            strongest_behaviors=strongest,
            weakest_behaviors=weakest,
            missed_evidence=missed,
            unnecessary_actions=unnecessary,
            critical_decision_points=decision_points,
            assumption_revisions=assumption_revisions,
            governance_decisions=governance_decisions_list,
            alternative_valid_trajectory=alt_trajectory,
            counterfactual_improvement=counterfactual,
            evaluator_confidence=confidence,
        )

    def _compute_overall(self, dimension_scores: list[DimensionScore]) -> float:
        """Compute overall as average of final dimension scores.

        Uses default weights from the scoring module.
        """
        from .scoring import DEFAULT_DIMENSION_WEIGHTS

        weights = DEFAULT_DIMENSION_WEIGHTS
        total_weight = 0.0
        weighted_sum = 0.0
        for ds in dimension_scores:
            w = weights.get(ds.dimension, 0.0)
            total_weight += w
            weighted_sum += ds.final_score * w
        if total_weight <= 0:
            return 0.0
        return round(weighted_sum / total_weight, 4)

    def _identify_strengths_weaknesses(
        self,
        dimension_scores: list[DimensionScore],
    ) -> tuple[list[str], list[str]]:
        """Identify strongest and weakest behaviors from dimension data."""
        strengths: list[str] = []
        weaknesses: list[str] = []
        for ds in sorted(dimension_scores, key=lambda x: x.final_score, reverse=True):
            if ds.final_score >= 0.7:
                strengths.extend(ds.strengths)
            elif ds.final_score <= 0.4:
                weaknesses.extend(ds.failures)
        return strengths[:5], weaknesses[:5]

    def _find_missed_evidence(self, dimension_scores: list[DimensionScore]) -> list[str]:
        """Identify evidence that was expected but not found."""
        missed: list[str] = []
        for ds in dimension_scores:
            if ds.final_score < 0.5 and ds.failures:
                missed.extend(
                    f"{ds.dimension}: {f}" for f in ds.failures
                )
        return missed[:5]

    def _find_unnecessary_actions(self, events: list[SimulationEvent]) -> list[str]:
        """Identify actions that appear unnecessary (repeated same action)."""
        action_counts: dict[str, int] = {}
        for e in events:
            at = e.payload.get("action_type", "unknown")
            action_counts[at] = action_counts.get(at, 0) + 1
        unnecessary: list[str] = []
        for action_type, count in action_counts.items():
            if count > 3:
                unnecessary.append(f"{action_type} (repeated {count} times)")
        return unnecessary[:5]

    def _identify_critical_decisions(self, events: list[SimulationEvent]) -> list[str]:
        """Identify critical decision points from the event stream."""
        critical_types = {
            "request_approval",
            "deploy_production",
            "submit_recommendation",
            "escalate",
            "terminate_service",
            "migrate_schema",
        }
        decisions: list[str] = []
        for e in events:
            at = e.payload.get("action_type", "")
            if at in critical_types:
                decisions.append(
                    f"{at} at event {e.event_id} (seq {e.sequence})"
                )
        return decisions

    def _count_assumption_revisions(self, events: list[SimulationEvent]) -> int:
        """Count events that represent assumption revisions."""
        revision_types = {"revise_assumption", "update_understanding", "correct_prior_belief"}
        return sum(
            1 for e in events if e.payload.get("action_type") in revision_types
        )

    def _extract_governance_decisions(self, events: list[SimulationEvent]) -> list[str]:
        """Extract governance-related decisions."""
        gov_types = {"request_approval", "register_risk", "authorize_action", "define_policy"}
        decisions: list[str] = []
        for e in events:
            at = e.payload.get("action_type", "")
            if at in gov_types:
                decisions.append(
                    f"{at} (event {e.event_id})"
                )
        return decisions

    def _generate_alternative_trajectory(
        self,
        dimension_scores: list[DimensionScore],
        case_definition: CaseDefinition,
    ) -> str:
        """Generate an alternative valid trajectory description based on weaknesses."""
        worst = sorted(dimension_scores, key=lambda x: x.final_score)[:2]
        if not worst:
            return "No alternative trajectory needed — all dimensions performed well."
        alt_parts: list[str] = []
        for ds in worst:
            if ds.failures:
                alt_parts.append(
                    f"In {ds.dimension}, addressing failures like "
                    f"'{ds.failures[0]}' could have improved the outcome."
                )
        if not alt_parts:
            return "All key areas performed adequately."
        return " ".join(alt_parts)

    def _generate_counterfactual(
        self,
        dimension_scores: list[DimensionScore],
        case_definition: CaseDefinition,
    ) -> str:
        """Generate a counterfactual improvement scenario."""
        worst = sorted(dimension_scores, key=lambda x: x.final_score)[:1]
        if not worst or worst[0].final_score >= 0.8:
            return "No significant counterfactual improvements identified."
        ds = worst[0]
        return (
            f"If the participant had performed better in '{ds.dimension}' "
            f"(score: {ds.final_score:.2f}), the overall outcome could have "
            f"been materially improved."
        )

    def _compute_evaluator_confidence(
        self,
        dimension_scores: list[DimensionScore],
    ) -> float:
        """Compute overall evaluator confidence from dimension confidences."""
        if not dimension_scores:
            return 0.5
        return round(
            sum(ds.confidence for ds in dimension_scores) / len(dimension_scores),
            4,
        )
