"""Tests for case validation CLI."""

from __future__ import annotations

from pathlib import Path

from afcs_api.cli import main
from afcs_case_schema.validator import CaseValidator, validate_case
from click.testing import CliRunner

# Path to the cases directory
CASES_DIR = Path(__file__).parent.parent.parent / "cases"
WRONG_USE_CASE = CASES_DIR / "wrong-use-case"


# ---------------------------------------------------------------------------
# Unit tests for validator module
# ---------------------------------------------------------------------------


def test_validate_valid_case() -> None:
    """A well-formed case should validate successfully."""
    result = validate_case(WRONG_USE_CASE)
    assert result.is_valid, f"Expected valid, got errors: {result.errors}"
    assert result.case_definition is not None
    assert result.case_definition.metadata.case_id == "wrong_use_case"


def test_validate_missing_directory() -> None:
    """A non-existent directory should produce an error."""
    result = validate_case("/nonexistent/path")
    assert not result.is_valid
    assert any("No .yaml file" in e for e in result.errors)


def test_validate_case_validator_class() -> None:
    """CaseValidator.validate should work the same."""
    result = CaseValidator.validate(WRONG_USE_CASE)
    assert result.is_valid
    assert result.case_definition is not None
    assert result.case_definition.metadata.case_id == "wrong_use_case"


def test_validate_invalid_yaml(tmp_path: Path) -> None:
    """Malformed YAML should produce a parse error."""
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("{invalid: [yaml")
    result = validate_case(tmp_path)
    assert not result.is_valid
    assert any("YAML" in e for e in result.errors)


def test_validate_file_direct(tmp_path: Path) -> None:
    """validate_file should work on a single file."""
    yaml_file = WRONG_USE_CASE / "v1.yaml"
    assert yaml_file.exists()
    result = CaseValidator.validate_file(yaml_file)
    assert result.is_valid
    assert result.case_definition is not None
    assert result.case_definition.metadata.case_id == "wrong_use_case"


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def test_cli_validate() -> None:
    """CLI validate command should succeed on valid case."""
    runner = CliRunner()
    result = runner.invoke(main, ["validate", str(WRONG_USE_CASE)])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "VALID" in result.output


def test_cli_validate_nonexistent() -> None:
    """CLI validate should fail on nonexistent path."""
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "/nonexistent"])
    assert result.exit_code != 0


def test_cli_inspect() -> None:
    """CLI inspect should print structured summary."""
    runner = CliRunner()
    result = runner.invoke(main, ["inspect", str(WRONG_USE_CASE)])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "wrong_use_case" in result.output
    assert "CTO" in result.output or "cto" in result.output
    assert "discovery" in result.output


def test_cli_simulate() -> None:
    """CLI simulate should run deterministic walkthrough."""
    runner = CliRunner()
    result = runner.invoke(main, ["simulate", str(WRONG_USE_CASE), "--seed", "42"])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "Simulation" in result.output
    assert "seed=42" in result.output


def test_cli_simulate_custom_seed() -> None:
    """Simulate should accept a custom seed."""
    runner = CliRunner()
    result = runner.invoke(main, ["simulate", str(WRONG_USE_CASE), "--seed", "99"])
    assert result.exit_code == 0
    assert "seed=99" in result.output


def test_cli_test_reachability() -> None:
    """CLI test-reachability should verify facts are reachable."""
    runner = CliRunner()
    result = runner.invoke(main, ["test-reachability", str(WRONG_USE_CASE)])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "reachable" in result.output.lower()


def test_cli_diff() -> None:
    """CLI diff should show differences between two versions."""
    v1 = WRONG_USE_CASE / "v1.yaml"
    v2 = WRONG_USE_CASE / "v2.yaml"
    runner = CliRunner()
    result = runner.invoke(main, ["diff", str(v1), str(v2)])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    assert "wrong_use_case" in result.output


def test_cli_diff_identical() -> None:
    """Diff on identical files should show no differences."""
    v1 = WRONG_USE_CASE / "v1.yaml"
    runner = CliRunner()
    result = runner.invoke(main, ["diff", str(v1), str(v1)])
    assert result.exit_code == 0
    assert "no differences" in result.output.lower()


def test_cli_diff_missing_file() -> None:
    """Diff on missing file should fail."""
    runner = CliRunner()
    result = runner.invoke(main, ["diff", "/nonexistent/a.yaml", "/nonexistent/b.yaml"])
    assert result.exit_code != 0


def test_cli_help() -> None:
    """CLI should respond to --help."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.output
    assert "simulate" in result.output
    assert "inspect" in result.output
    assert "test-reachability" in result.output
    assert "diff" in result.output
