from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from afcs_case_schema.models import CaseDefinition


def load_case(path: Path) -> CaseDefinition:
    """Load a single YAML case definition file and validate it."""
    if not path.exists():
        raise FileNotFoundError(f"Case file not found: {path}")
    if path.suffix.lower() not in {".yaml", ".yml"}:
        msg = f"Expected a .yaml or .yml file, got: {path.suffix}"
        raise ValueError(msg)

    raw: dict[str, Any] = _load_yaml(path)
    return CaseDefinition.model_validate(raw)


def load_case_dir(dir_path: Path) -> list[CaseDefinition]:
    """Load all YAML case definitions from a directory."""
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    yaml_files = sorted(p for p in dir_path.iterdir() if p.suffix.lower() in {".yaml", ".yml"})
    if not yaml_files:
        msg = f"No .yaml or .yml files found in {dir_path}"
        raise FileNotFoundError(msg)

    cases: list[CaseDefinition] = []
    errors: list[tuple[Path, Exception]] = []

    for path in yaml_files:
        try:
            cases.append(load_case(path))
        except Exception as exc:
            errors.append((path, exc))

    if errors:
        msg_parts = [f"Failed to load {len(errors)} case(s):"]
        for err_path, err_exc in errors:
            msg_parts.append(f"  {err_path.name}: {err_exc}")
        raise ValueError("\n".join(msg_parts))

    return cases


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"YAML file must contain a mapping (dict), got {type(raw).__name__}")
    return raw
