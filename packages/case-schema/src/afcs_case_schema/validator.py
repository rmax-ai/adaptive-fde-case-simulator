"""Case validation logic — load YAML, validate against existing CaseDefinition model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from afcs_case_schema.models import CaseDefinition


class ValidationResult:
    """Result of validating a case definition."""

    def __init__(self, case_dir: str) -> None:
        self.case_dir = case_dir
        self.is_valid: bool = False
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.case_definition: CaseDefinition | None = None

    def __bool__(self) -> bool:
        return self.is_valid

    def summary(self) -> str:
        lines: list[str] = []
        if self.case_definition:
            m = self.case_definition.metadata
            lines.append(f"Case: {m.case_id} — {m.title} (v{m.version}, {m.difficulty.value})")
            lines.append(f"  Domain: {m.domain}")
            lines.append(f"  Status: {m.status.value}")
            dims = self.case_definition.evaluation.dimensions
            lines.append(
                f"  Evaluation dimensions: {len(dims)}"
                + (f" — {', '.join(d.name for d in dims)}" if dims else "")
            )
            stakeholders = self.case_definition.organization.stakeholders
            lines.append(f"  Stakeholders: {len(stakeholders)}")
        if self.is_valid:
            lines.append("Status: ✅ VALID")
        else:
            lines.append("Status: ❌ INVALID")
        for e in self.errors:
            lines.append(f"  Error: {e}")
        for w in self.warnings:
            lines.append(f"  Warning: {w}")
        return "\n".join(lines)


def find_case_yaml(case_dir: str | Path) -> Path | None:
    """Find the first .yaml file in the given directory."""
    d = Path(case_dir)
    if not d.is_dir():
        return None
    for f in sorted(d.iterdir()):
        if f.suffix in (".yaml", ".yml") and f.is_file():
            return f
    return None


def load_case_yaml(path: str | Path) -> dict[str, Any]:
    """Load a case YAML file and return the parsed dict."""
    with open(path) as f:
        return yaml.safe_load(f)


def validate_case(case_dir: str | Path) -> ValidationResult:
    """Load and validate a case definition from a directory."""
    result = ValidationResult(str(case_dir))
    yaml_path = find_case_yaml(case_dir)

    if yaml_path is None:
        result.errors.append(f"No .yaml file found in {case_dir}")
        return result

    try:
        data = load_case_yaml(yaml_path)
    except yaml.YAMLError as exc:
        result.errors.append(f"YAML parse error: {exc}")
        return result

    if data is None:
        result.errors.append("YAML file is empty")
        return result

    try:
        case_def = CaseDefinition.model_validate(data)
    except ValidationError as exc:
        for err in exc.errors():
            loc = " -> ".join(str(p) for p in err["loc"])
            result.errors.append(f"{loc}: {err['msg']}")
        return result

    # Additional semantic checks
    if not case_def.organization.stakeholders:
        result.warnings.append("No stakeholders defined")

    if not case_def.evaluation.dimensions:
        result.warnings.append("No evaluation dimensions defined")

    dim_weight_sum = sum(d.weight for d in case_def.evaluation.dimensions)
    if case_def.evaluation.dimensions and abs(dim_weight_sum - 1.0) > 0.001:
        result.warnings.append(
            f"Evaluation dimension weights sum to {dim_weight_sum:.3f}, expected ~1.0"
        )

    result.is_valid = True
    result.case_definition = case_def
    return result


class CaseValidator:
    """High-level validator wrapping validate_case."""

    @staticmethod
    def validate(case_dir: str | Path) -> ValidationResult:
        return validate_case(case_dir)

    @staticmethod
    def validate_file(yaml_path: str | Path) -> ValidationResult:
        """Validate a single YAML file directly."""
        result = ValidationResult(str(yaml_path))
        try:
            data = load_case_yaml(yaml_path)
        except yaml.YAMLError as exc:
            result.errors.append(f"YAML parse error: {exc}")
            return result
        if data is None:
            result.errors.append("YAML file is empty")
            return result
        try:
            case_def = CaseDefinition.model_validate(data)
        except ValidationError as exc:
            for err in exc.errors():
                loc = " -> ".join(str(p) for p in err["loc"])
                result.errors.append(f"{loc}: {err['msg']}")
            return result
        result.is_valid = True
        result.case_definition = case_def
        return result
