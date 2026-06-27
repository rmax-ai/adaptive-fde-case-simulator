from __future__ import annotations

from afcs_case_schema.models import CaseDefinition
from afcs_domain.events import SimulationEvent
from afcs_domain.state import CanonicalState
from pydantic import BaseModel

from .validators import ValidatorFn, ValidatorResult

# ── Validator Registry ───────────────────────────────────────────────────────────


class ValidatorRegistry(BaseModel):
    """Registry that holds a collection of named validators and can run them."""

    validators: dict[str, ValidatorFn] = {}

    def register(self, name: str, fn: ValidatorFn) -> None:
        """Register a single validator by name."""
        self.validators[name] = fn

    def register_many(self, validators: dict[str, ValidatorFn]) -> None:
        """Register multiple validators at once."""
        self.validators.update(validators)

    def run_all(
        self,
        events: list[SimulationEvent],
        final_state: CanonicalState,
        case_definition: CaseDefinition,
    ) -> list[ValidatorResult]:
        """Run every registered validator and return the results."""
        results: list[ValidatorResult] = []
        for _name, fn in self.validators.items():
            result = fn(events, final_state, case_definition)
            results.append(result)
        return results

    def run_single(
        self,
        name: str,
        events: list[SimulationEvent],
        final_state: CanonicalState,
        case_definition: CaseDefinition,
    ) -> ValidatorResult | None:
        """Run a single named validator, returning None if not found."""
        fn = self.validators.get(name)
        if fn is None:
            return None
        return fn(events, final_state, case_definition)

    model_config = {"extra": "forbid"}
