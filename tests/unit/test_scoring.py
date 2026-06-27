"""Tests for dimension scoring, weighting, and adjudication."""

from __future__ import annotations

import pytest
from afcs_evaluation_engine.scoring import (
    DimensionScore,
    compute_dimension_scores,
    compute_overall_score,
    default_weights,
)
from afcs_evaluation_engine.validators import ValidatorResult, build_default_validators

# ── Fixtures ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def all_pass_results() -> list[ValidatorResult]:
    """All 12 validators passing with score 1.0."""
    validators = build_default_validators()
    return [
        ValidatorResult(
            validator_name=name,
            passed=True,
            score=1.0,
            evidence_event_ids=["evt-1"],
            details=f"{name} passed",
        )
        for name in validators
    ]


@pytest.fixture
def all_fail_results() -> list[ValidatorResult]:
    """All 12 validators failing with score 0.0."""
    validators = build_default_validators()
    return [
        ValidatorResult(
            validator_name=name,
            passed=False,
            score=0.0,
            evidence_event_ids=[],
            details=f"{name} failed",
        )
        for name in validators
    ]


@pytest.fixture
def mixed_results() -> list[ValidatorResult]:
    """Mix of passing and failing validators."""
    validators = build_default_validators()
    results: list[ValidatorResult] = []
    for i, name in enumerate(validators):
        passed = i % 2 == 0
        results.append(
            ValidatorResult(
                validator_name=name,
                passed=passed,
                score=1.0 if passed else 0.0,
                evidence_event_ids=[f"evt-{i}"] if passed else [],
                details=f"{name}: {'pass' if passed else 'fail'}",
            )
        )
    return results


# ── Tests for default_weights ────────────────────────────────────────────────────


class TestDefaultWeights:
    def test_returns_copy(self):
        w1 = default_weights()
        w2 = default_weights()
        assert w1 == w2
        assert w1 is not w2  # Different objects

    def test_contains_all_six_dimensions(self):
        w = default_weights()
        assert set(w.keys()) == {
            "discovery",
            "technical",
            "evaluation_quality",
            "delivery",
            "governance",
            "operational_sustainability",
        }

    def test_weights_sum_to_one(self):
        w = default_weights()
        assert abs(sum(w.values()) - 1.0) < 0.001


# ── Tests for compute_dimension_scores ───────────────────────────────────────────


class TestComputeDimensionScores:
    def test_all_pass_gives_max_scores(self, all_pass_results):
        scores = compute_dimension_scores(all_pass_results, None)  # type: ignore[arg-type]
        assert len(scores) == 6
        for ds in scores:
            assert ds.machine_score == pytest.approx(1.0)
            assert ds.final_score == pytest.approx(1.0)

    def test_all_fail_gives_zero_scores(self, all_fail_results):
        scores = compute_dimension_scores(all_fail_results, None)  # type: ignore[arg-type]
        for ds in scores:
            assert ds.machine_score == pytest.approx(0.0)
            assert ds.final_score == pytest.approx(0.0)

    def test_mixed_results(self, mixed_results):
        scores = compute_dimension_scores(mixed_results, None)  # type: ignore[arg-type]
        discovery = next(ds for ds in scores if ds.dimension == "discovery")
        # discovery: baseline_defined(pass), success_criteria_defined(fail),
        #            decisive_evidence_inspected(pass) -> 2/3
        assert discovery.machine_score == pytest.approx(2.0 / 3.0, abs=0.01)

    def test_custom_weights(self, all_pass_results):
        custom_weights = {"discovery": 1.0}
        scores = compute_dimension_scores(all_pass_results, None, dimension_weights=custom_weights)  # type: ignore[arg-type]
        assert len(scores) == 1
        assert scores[0].dimension == "discovery"

    def test_human_scores_blend(self, all_pass_results):
        human_scores = {"discovery": 0.5}
        scores = compute_dimension_scores(
            all_pass_results,
            None,  # type: ignore[arg-type]
            human_scores=human_scores,
        )
        discovery = next(ds for ds in scores if ds.dimension == "discovery")
        # 0.7 * 1.0 + 0.3 * 0.5 = 0.85
        assert discovery.final_score == pytest.approx(0.85)

    def test_human_score_none(self, all_pass_results):
        scores = compute_dimension_scores(all_pass_results, None)  # type: ignore[arg-type]
        assert all(ds.human_score is None for ds in scores)

    def test_each_dimension_has_strengths_and_failures(self, mixed_results):
        scores = compute_dimension_scores(mixed_results, None)  # type: ignore[arg-type]
        for ds in scores:
            assert isinstance(ds.strengths, list)
            assert isinstance(ds.failures, list)
            assert isinstance(ds.uncertainties, list)


# ── Tests for compute_overall_score ──────────────────────────────────────────────


class TestComputeOverallScore:
    def test_all_perfect_gives_one(self, all_pass_results):
        scores = compute_dimension_scores(all_pass_results, None)  # type: ignore[arg-type]
        overall = compute_overall_score(scores)
        assert overall == pytest.approx(1.0)

    def test_all_zero_gives_zero(self, all_fail_results):
        scores = compute_dimension_scores(all_fail_results, None)  # type: ignore[arg-type]
        overall = compute_overall_score(scores)
        assert overall == pytest.approx(0.0)

    def test_weighted_correctly(self):
        """Manually verify weighted average."""
        scores = [
            DimensionScore(
                dimension="discovery",
                machine_score=0.8,
                final_score=0.8,
                confidence=0.8,
                evidence_event_ids=[],
                strengths=[],
                failures=[],
                uncertainties=[],
            ),
            DimensionScore(
                dimension="technical",
                machine_score=0.4,
                final_score=0.4,
                confidence=0.5,
                evidence_event_ids=[],
                strengths=[],
                failures=[],
                uncertainties=[],
            ),
        ]
        weights = {"discovery": 0.30, "technical": 0.20}
        overall = compute_overall_score(scores, weights)
        expected = (0.8 * 0.30 + 0.4 * 0.20) / (0.30 + 0.20)
        assert overall == pytest.approx(expected)


# ── Tests for DimensionScore model ───────────────────────────────────────────────


class TestDimensionScoreModel:
    def test_valid_construction(self):
        ds = DimensionScore(
            dimension="discovery",
            machine_score=0.75,
            final_score=0.75,
            confidence=0.6,
            evidence_event_ids=["evt-1"],
            strengths=["good discovery"],
            failures=[],
            uncertainties=[],
        )
        assert ds.dimension == "discovery"
        assert ds.machine_score == 0.75

    def test_invalid_machine_score_raises(self):
        with pytest.raises(ValueError):
            DimensionScore(
                dimension="discovery",
                machine_score=1.5,  # > 1.0
                final_score=0.75,
                confidence=0.5,
            )

    def test_invalid_negative_score_raises(self):
        with pytest.raises(ValueError):
            DimensionScore(
                dimension="discovery",
                machine_score=-0.1,  # < 0.0
                final_score=0.0,
                confidence=0.5,
            )

    def test_human_score_optional(self):
        ds = DimensionScore(
            dimension="discovery",
            machine_score=0.5,
            final_score=0.5,
            confidence=0.5,
        )
        assert ds.human_score is None

    def test_default_factory_works(self):
        ds = DimensionScore(
            dimension="discovery",
            machine_score=0.5,
            final_score=0.5,
            confidence=0.5,
        )
        assert ds.evidence_event_ids == []
        assert ds.strengths == []
        assert ds.failures == []
        assert ds.uncertainties == []
