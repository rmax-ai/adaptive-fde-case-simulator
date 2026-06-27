"""Structural diff tool for AFCS case definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class DiffChange:
    """A single change between two case versions."""

    def __init__(self, path: str, old_value: Any, new_value: Any) -> None:
        self.path = path
        self.old_value = old_value
        self.new_value = new_value

    def __str__(self) -> str:
        return f"  {self.path}: {self.old_value!r} → {self.new_value!r}"


class DiffResult:
    """Result of a structural diff between two cases."""

    def __init__(self, case_a_id: str, case_b_id: str) -> None:
        self.case_a_id = case_a_id
        self.case_b_id = case_b_id
        self.changes: list[DiffChange] = []
        self.added_fields: list[str] = []
        self.removed_fields: list[str] = []
        self.has_differences: bool = False

    def summary(self) -> str:
        if not self.has_differences:
            return "Cases are structurally identical (no differences found)."
        lines: list[str] = [
            f"Diff: {self.case_a_id} ↔ {self.case_b_id}",
            f"  Changes: {len(self.changes)}",
            f"  Added fields: {len(self.added_fields)}",
            f"  Removed fields: {len(self.removed_fields)}",
            "",
        ]
        if self.changes:
            lines.append("Changed:")
            lines.extend(str(c) for c in self.changes)
        if self.added_fields:
            lines.append("Added:")
            for f in self.added_fields:
                lines.append(f"  + {f}")
        if self.removed_fields:
            lines.append("Removed:")
            for f in self.removed_fields:
                lines.append(f"  - {f}")
        return "\n".join(lines)


def _flatten_dict(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Recursively flatten a nested dict into dot-separated keys."""
    result: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(_flatten_dict(v, key))
        elif isinstance(v, list):
            result[key] = tuple(
                _flatten_dict(item, key) if isinstance(item, dict) else item for item in v
            )
            result[f"{key}.#"] = len(v)
        else:
            result[key] = v
    return result


def compute_diff(case_a_path: str | Path, case_b_path: str | Path) -> DiffResult:
    """Compute a structural diff between two case YAML files."""
    with open(case_a_path) as f:
        data_a = yaml.safe_load(f)
    with open(case_b_path) as f:
        data_b = yaml.safe_load(f)

    if not isinstance(data_a, dict):
        raise ValueError(f"{case_a_path} does not contain a YAML mapping")
    if not isinstance(data_b, dict):
        raise ValueError(f"{case_b_path} does not contain a YAML mapping")

    case_a_id = data_a.get("metadata", {}).get("case_id", str(case_a_path))
    case_b_id = data_b.get("metadata", {}).get("case_id", str(case_b_path))

    result = DiffResult(case_a_id, case_b_id)
    flat_a = _flatten_dict(data_a)
    flat_b = _flatten_dict(data_b)

    keys_a = set(flat_a.keys())
    keys_b = set(flat_b.keys())

    result.added_fields = sorted(keys_b - keys_a)
    result.removed_fields = sorted(keys_a - keys_b)
    common_keys = keys_a & keys_b

    for key in sorted(common_keys):
        val_a = flat_a[key]
        val_b = flat_b[key]
        if val_a != val_b:
            result.changes.append(DiffChange(key, val_a, val_b))

    result.has_differences = bool(result.changes or result.added_fields or result.removed_fields)
    return result


class CaseDiffer:
    """High-level differ for case definitions."""

    @staticmethod
    def diff(case_a_path: str | Path, case_b_path: str | Path) -> DiffResult:
        return compute_diff(case_a_path, case_b_path)
