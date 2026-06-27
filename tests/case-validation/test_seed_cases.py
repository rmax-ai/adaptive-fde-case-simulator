"""Tests for seed cases — validates all 3 seed YAMLs pass schema validation and reachability."""

from __future__ import annotations

from pathlib import Path

import pytest
from afcs_case_schema.reachability import check_reachability
from afcs_case_schema.validator import validate_case

# Path to the cases directory
CASES_DIR = Path(__file__).resolve().parent.parent.parent / "cases"

# Map case names to their directory relative to CASES_DIR
SEED_CASES = {
    "wrong_use_case": CASES_DIR / "wrong-use-case",
    "unsafe_autonomy": CASES_DIR / "unsafe-autonomy",
    "unmaintainable_prototype": CASES_DIR / "unmaintainable-prototype",
}


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSeedCaseValidation:
    """Each seed case must pass schema validation without errors."""

    @pytest.mark.parametrize(
        "case_label, case_dir",
        list(SEED_CASES.items()),
        ids=list(SEED_CASES.keys()),
    )
    def test_case_validates(self, case_label: str, case_dir: Path) -> None:
        result = validate_case(case_dir)
        assert result.is_valid, f"Case '{case_label}' failed schema validation:\n" + "\n".join(
            f"  - {e}" for e in result.errors
        )
        assert result.case_definition is not None
        assert result.case_definition.metadata.case_id == case_label

    @pytest.mark.parametrize(
        "case_label, case_dir",
        list(SEED_CASES.items()),
        ids=list(SEED_CASES.keys()),
    )
    def test_case_has_stakeholders(self, case_label: str, case_dir: Path) -> None:
        result = validate_case(case_dir)
        assert result.is_valid
        assert result.case_definition is not None
        stakeholders = result.case_definition.organization.stakeholders
        assert len(stakeholders) >= 1, f"Case '{case_label}' must have at least 1 stakeholder"

    @pytest.mark.parametrize(
        "case_label, case_dir",
        list(SEED_CASES.items()),
        ids=list(SEED_CASES.keys()),
    )
    def test_case_has_evaluation_dimensions(self, case_label: str, case_dir: Path) -> None:
        result = validate_case(case_dir)
        assert result.is_valid
        assert result.case_definition is not None
        dims = result.case_definition.evaluation.dimensions
        assert len(dims) >= 1, f"Case '{case_label}' must have at least 1 evaluation dimension"

    @pytest.mark.parametrize(
        "case_label, case_dir",
        list(SEED_CASES.items()),
        ids=list(SEED_CASES.keys()),
    )
    def test_case_has_target_facts(self, case_label: str, case_dir: Path) -> None:
        result = validate_case(case_dir)
        assert result.is_valid
        assert result.case_definition is not None
        target_facts = result.case_definition.evaluation.target_facts
        assert len(target_facts) >= 1, f"Case '{case_label}' must have at least 1 target_fact"

    @pytest.mark.parametrize(
        "case_label, case_dir",
        list(SEED_CASES.items()),
        ids=list(SEED_CASES.keys()),
    )
    def test_case_has_metadata_required_fields(self, case_label: str, case_dir: Path) -> None:
        result = validate_case(case_dir)
        assert result.is_valid
        assert result.case_definition is not None
        meta = result.case_definition.metadata
        assert meta.case_id == case_label
        assert meta.version == "1.0.0"
        assert meta.status.value == "published"
        assert meta.domain == "enterprise-support"

    @pytest.mark.parametrize(
        "case_label, case_dir",
        list(SEED_CASES.items()),
        ids=list(SEED_CASES.keys()),
    )
    def test_case_has_budget(self, case_label: str, case_dir: Path) -> None:
        result = validate_case(case_dir)
        assert result.is_valid
        assert result.case_definition is not None
        budget = result.case_definition.business.budget
        assert isinstance(budget, dict), "Budget must be a dict"
        assert "amount" in budget, "Budget must have 'amount'"
        assert "currency" in budget, "Budget must have 'currency'"
        assert budget["currency"] == "USD"


# ---------------------------------------------------------------------------
# Reachability tests
# ---------------------------------------------------------------------------


class TestSeedCaseReachability:
    """All target_facts in each seed case must pass reachability checks."""

    @pytest.mark.parametrize(
        "case_label, case_dir",
        list(SEED_CASES.items()),
        ids=list(SEED_CASES.keys()),
    )
    def test_all_target_facts_reachable(self, case_label: str, case_dir: Path) -> None:
        result = validate_case(case_dir)
        assert result.is_valid
        assert result.case_definition is not None

        r = check_reachability(result.case_definition)
        assert r.all_reachable, f"Case '{case_label}' has unreachable target_facts:\n" + "\n".join(
            f"  - {fact}" for fact in r.unreachable_facts
        )
        assert not r.errors, f"Case '{case_label}' reachability check had errors:\n" + "\n".join(
            f"  - {e}" for e in r.errors
        )

    @pytest.mark.parametrize(
        "case_label, case_dir",
        list(SEED_CASES.items()),
        ids=list(SEED_CASES.keys()),
    )
    def test_each_target_fact_reported_reachable(self, case_label: str, case_dir: Path) -> None:
        result = validate_case(case_dir)
        assert result.is_valid
        assert result.case_definition is not None

        r = check_reachability(result.case_definition)
        for fact in result.case_definition.evaluation.target_facts:
            assert r.reachable.get(fact, False), (
                f"Target fact '{fact}' in case '{case_label}' is not marked reachable"
            )


# ---------------------------------------------------------------------------
# Semantic checks
# ---------------------------------------------------------------------------


class TestSeedCaseSemantics:
    """Higher-level checks that seed cases are well-formed."""

    def test_all_seed_cases_exist(self) -> None:
        """Verify all seed case directories and their YAML files exist."""
        for _label, case_dir in SEED_CASES.items():
            assert case_dir.is_dir(), f"Case directory not found: {case_dir}"
            yaml_files = sorted(case_dir.glob("*.yaml"))
            assert len(yaml_files) >= 1, f"No .yaml files found in {case_dir}"

    def test_all_cases_have_different_budgets(self) -> None:
        """Seed cases should have distinct budgets to reflect different scopes."""
        budgets: dict[str, float] = {}
        for label, case_dir in SEED_CASES.items():
            result = validate_case(case_dir)
            assert result.is_valid and result.case_definition is not None
            amount = float(result.case_definition.business.budget.get("amount", 0))
            budgets[label] = amount

        # All budgets should be different (wrong_use_case=50000, unsafe_autonomy=75000,
        # unmaintainable_prototype=120000)
        assert len(set(budgets.values())) == len(budgets), (
            f"All seed cases should have distinct budgets: {budgets}"
        )

    def test_seed_case_ids_use_underscores(self) -> None:
        """All seed case_ids must use underscores as specified."""
        for case_dir in SEED_CASES.values():
            result = validate_case(case_dir)
            if result.is_valid and result.case_definition is not None:
                cid = result.case_definition.metadata.case_id
                assert "_" in cid, f"case_id '{cid}' does not use underscores"
                assert cid.islower(), f"case_id '{cid}' must be lowercase"
