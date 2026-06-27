from __future__ import annotations

from afcs_case_schema.models import CaseDefinition
from pydantic import BaseModel, Field

from .validators import ValidatorResult

# ── Default weights (from architecture spec) ─────────────────────────────────────


DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "discovery": 0.30,
    "technical": 0.20,
    "evaluation_quality": 0.10,
    "delivery": 0.25,
    "governance": 0.10,
    "operational_sustainability": 0.05,
}


def default_weights() -> dict[str, float]:
    """Return a copy of the default dimension weights."""
    return dict(DEFAULT_DIMENSION_WEIGHTS)


# ── Dimension Score Model ────────────────────────────────────────────────────────


class DimensionScore(BaseModel):
    """Score for a single evaluation dimension."""

    dimension: str
    machine_score: float = Field(ge=0.0, le=1.0)
    human_score: float | None = Field(default=None, ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_event_ids: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid", "frozen": True}


# ── Dimension → Validator mapping ────────────────────────────────────────────────


DIMENSION_VALIDATOR_MAP: dict[str, list[str]] = {
    "discovery": [
        "baseline_defined",
        "success_criteria_defined",
        "decisive_evidence_inspected",
    ],
    "technical": [
        "decisive_evidence_inspected",
        "irreversible_action_protected",
    ],
    "evaluation_quality": [
        "evaluation_includes_failure_cases",
        "critical_risk_registered",
    ],
    "delivery": [
        "deadline_respected",
        "budget_respected",
        "owner_assigned",
    ],
    "governance": [
        "required_approval_obtained",
        "prohibited_action_avoided",
        "critical_risk_registered",
    ],
    "operational_sustainability": [
        "rollback_defined",
        "irreversible_action_protected",
    ],
}


# ── Scoring functions ────────────────────────────────────────────────────────────


def compute_dimension_scores(
    validator_results: list[ValidatorResult],
    case_definition: CaseDefinition,
    dimension_weights: dict[str, float] | None = None,
    human_scores: dict[str, float] | None = None,
) -> list[DimensionScore]:
    """Compute dimension scores from validator results.

    Each dimension's machine_score is the average of its mapped validators.
    final_score is adjudicated from machine_score and optional human_score.
    """
    weights = dimension_weights or DEFAULT_DIMENSION_WEIGHTS
    human_scores = human_scores or {}
    scores: list[DimensionScore] = []

    # Build lookup: validator_name -> ValidatorResult
    result_map: dict[str, ValidatorResult] = {r.validator_name: r for r in validator_results}

    for dimension in weights:
        mapped = DIMENSION_VALIDATOR_MAP.get(dimension, [])
        if not mapped:
            scores.append(
                DimensionScore(
                    dimension=dimension,
                    machine_score=0.0,
                    final_score=0.0,
                    confidence=0.0,
                    evidence_event_ids=[],
                    strengths=[],
                    failures=[],
                    uncertainties=["No validators mapped to this dimension."],
                )
            )
            continue

        relevant_results = [result_map.get(v) for v in mapped if v in result_map]
        if not relevant_results:
            scores.append(
                DimensionScore(
                    dimension=dimension,
                    machine_score=0.0,
                    final_score=0.0,
                    confidence=0.0,
                    evidence_event_ids=[],
                    strengths=[],
                    failures=[],
                    uncertainties=["No validator results available for this dimension."],
                )
            )
            continue

        machine_score = sum(r.score for r in relevant_results) / len(relevant_results)
        evidence_ids: list[str] = []
        strengths: list[str] = []
        failures: list[str] = []
        uncertainties: list[str] = []
        for r in relevant_results:
            evidence_ids.extend(r.evidence_event_ids)
            if r.passed:
                strengths.append(f"{r.validator_name}: {r.details}")
            else:
                failures.append(f"{r.validator_name}: {r.details}")
            if r.score > 0 and r.score < 1:
                uncertainties.append(f"{r.validator_name}: partial score {r.score:.2f}")

        human_score = human_scores.get(dimension)
        final_score = _adjudicate(machine_score, human_score)

        # Confidence: higher if we have human score or lots of evidence
        confidence = _compute_confidence(machine_score, human_score, evidence_ids)

        scores.append(
            DimensionScore(
                dimension=dimension,
                machine_score=round(machine_score, 4),
                human_score=human_score,
                final_score=round(final_score, 4),
                confidence=round(confidence, 4),
                evidence_event_ids=evidence_ids,
                strengths=strengths,
                failures=failures,
                uncertainties=uncertainties,
            )
        )

    return scores


def _adjudicate(machine_score: float, human_score: float | None) -> float:
    """Adjudicate between machine and human scores.

    If human_score is provided, blend: 0.7 * machine + 0.3 * human.
    Otherwise, use machine_score directly.
    """
    if human_score is not None:
        return 0.7 * machine_score + 0.3 * human_score
    return machine_score


def _compute_confidence(
    machine_score: float,
    human_score: float | None,
    evidence_ids: list[str],
) -> float:
    """Compute confidence level based on available data.

    Base = 0.5. +0.2 if human score available. +0.05 per evidence item (capped at +0.3).
    """
    base = 0.5
    if human_score is not None:
        base += 0.2
    base += min(0.3, len(evidence_ids) * 0.05)
    return min(1.0, base)


def compute_overall_score(
    dimension_scores: list[DimensionScore],
    weights: dict[str, float] | None = None,
) -> float:
    """Compute weighted overall score from dimension scores."""
    w = weights or DEFAULT_DIMENSION_WEIGHTS
    total_weight = 0.0
    weighted_sum = 0.0
    for ds in dimension_scores:
        weight = w.get(ds.dimension, 0.0)
        total_weight += weight
        weighted_sum += ds.final_score * weight
    if total_weight <= 0:
        return 0.0
    return round(weighted_sum / total_weight, 4)
