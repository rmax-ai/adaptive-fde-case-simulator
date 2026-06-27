"""Reachability checker — verify all hidden facts can be reached via action paths."""

from __future__ import annotations

from afcs_case_schema.models import CaseDefinition


class ReachabilityResult:
    """Result of a reachability analysis."""

    def __init__(self) -> None:
        self.reachable: dict[str, bool] = {}
        self.errors: list[str] = []
        self.unreachable_facts: list[str] = []

    @property
    def all_reachable(self) -> bool:
        return len(self.unreachable_facts) == 0

    def summary(self) -> str:
        lines: list[str] = []
        if self.all_reachable and not self.errors:
            lines.append("Status: ✅ ALL target facts are reachable")
        else:
            lines.append("Status: ❌ Some target facts are unreachable")
            for fact in self.unreachable_facts:
                lines.append(f"  • {fact}: no action path found")
        for fact, reached in sorted(self.reachable.items()):
            icon = "✅" if reached else "❌"
            lines.append(f"  {icon} {fact}")
        if self.errors:
            lines.append("Warnings:")
            for e in self.errors:
                lines.append(f"  {e}")
        return "\n".join(lines)


def _slug(value: str) -> str:
    """Convert text to a lowercase underscore-separated slug."""
    result = value.lower()
    for ch in (" ", "-", ",", ".", "'", '"', "!", "?", ":", ";", "(", ")", "/", "\\"):
        result = result.replace(ch, "_")
    # Collapse multiple underscores
    while "__" in result:
        result = result.replace("__", "_")
    return result[:80]


def _collect_action_paths(case_def: CaseDefinition) -> list[str]:
    """Build a list of possible action identifiers from the case definition."""
    return [action.action_type for action in case_def.actions.allowed]


def _collect_hidden_fact_keys(case_def: CaseDefinition) -> set[str]:
    """Collect all key-like identifiers that count as 'reachable' knowledge."""
    keys: set[str] = set()

    # Helper to add both original and slug versions
    def _add(value: str) -> None:
        keys.add(value)
        keys.add(_slug(value))

    # Hidden defects from technical state
    for defect in case_def.technical.hidden_defects:
        _add(defect)

    # Technical constraints
    for tc in case_def.technical.technical_constraints:
        _add(tc)

    # Business risks
    for risk in case_def.business.business_risks:
        _add(risk)

    # Stakeholder hidden_incentives, false_beliefs, knowledge
    for stakeholder in case_def.organization.stakeholders:
        for incentive in stakeholder.hidden_incentives:
            _add(incentive)
        for belief in stakeholder.false_beliefs:
            _add(belief)
        for knowledge in stakeholder.knowledge:
            _add(knowledge)

    # Action types
    for path in _collect_action_paths(case_def):
        keys.add(path)

    # Evaluation dimension names
    for dim in case_def.evaluation.dimensions:
        keys.add(dim.name)
        for criterion in dim.criteria:
            _add(criterion)

    # Valid strategy patterns
    for pattern in case_def.evaluation.valid_strategy_patterns:
        _add(pattern)

    return keys


def check_reachability(case_def: CaseDefinition) -> ReachabilityResult:
    """Check that every target fact in evaluation.target_facts is reachable.

    Performs static analysis by matching target fact names against:
    - Hidden defect descriptions from TechnicalState
    - Stakeholder hidden incentives/knowledge/false beliefs
    - Action types
    - Evaluation dimension names
    - Evaluation criteria text
    - Business risks
    """
    result = ReachabilityResult()

    if not case_def.evaluation.target_facts:
        result.errors.append("No target_facts defined in evaluation config")
        return result

    available = _collect_hidden_fact_keys(case_def)

    # Also build a slug-indexed version of all available keys for fuzzy matching
    available_slugs = {_slug(k): k for k in available}

    for fact in case_def.evaluation.target_facts:
        # Exact match (case-sensitive)
        if fact in available:
            result.reachable[fact] = True
            continue

        # Slug match (case-insensitive)
        fact_slug = _slug(fact)
        if fact_slug in available_slugs:
            result.reachable[fact] = True
            continue

        # Partial match (only for strings > 3 chars to avoid false positives)
        if len(fact) > 3:
            matched = False
            for k in available:
                if fact_slug in _slug(k) or _slug(k) in fact_slug:
                    # Only match if the longer string is at least 50% of the shorter
                    shorter = min(len(fact_slug), len(_slug(k)))
                    if shorter > 0:
                        result.reachable[fact] = True
                        matched = True
                        break
            if matched:
                continue

        result.reachable[fact] = False
        result.unreachable_facts.append(fact)

    return result


class ReachabilityChecker:
    """High-level reachability checker."""

    @staticmethod
    def check(case_def: CaseDefinition) -> ReachabilityResult:
        return check_reachability(case_def)
