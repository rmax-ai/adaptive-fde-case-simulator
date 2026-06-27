from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from afcs_case_schema.loader import load_case, load_case_dir
from afcs_case_schema.models import CaseDefinition, CaseStatus, DifficultyLevel

TESTS_DIR = Path(__file__).resolve().parent
FIXTURE_PATH = TESTS_DIR / "valid_case_fixture.yaml"


class TestLoadCase:
    def test_load_valid_yaml(self) -> None:
        case = load_case(FIXTURE_PATH)
        assert isinstance(case, CaseDefinition)
        assert case.metadata.case_id == "test_hello_world"
        assert case.metadata.version == "1.0.0"
        assert case.metadata.status == CaseStatus.draft
        assert case.metadata.difficulty == DifficultyLevel.introductory

    def test_load_valid_yaml_contents(self) -> None:
        case = load_case(FIXTURE_PATH)
        assert case.business.stated_goal == "Demonstrate that the simulation works"
        assert len(case.technical.systems) == 1
        assert case.technical.systems[0].name == "test_system"
        assert len(case.organization.stakeholders) == 1
        assert case.organization.stakeholders[0].stakeholder_id == "stakeholder_test"
        assert len(case.evidence.artifacts) == 1
        assert case.evidence.artifacts[0].artifact_id == "doc_001"
        assert len(case.actions.allowed) == 1
        assert case.actions.allowed[0].action_type == "test_action"

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_case(Path("/nonexistent/file.yaml"))

    def test_wrong_extension(self, tmp_path: Path) -> None:
        """Test that a non-YAML extension raises ValueError."""
        # File must exist for the extension check to be reached
        non_yaml = tmp_path / "test.json"
        non_yaml.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match=r"Expected a .yaml or .yml"):
            load_case(non_yaml)

    def test_not_a_directory_in_dir_load(self) -> None:
        with pytest.raises(NotADirectoryError):
            load_case_dir(Path("/nonexistent/dir"))


class TestLoadCaseDir:
    def test_load_directory_with_fixture(self) -> None:
        cases = load_case_dir(TESTS_DIR)
        yaml_files = [c.metadata.case_id for c in cases]
        assert "test_hello_world" in yaml_files

    def test_load_directory_no_yaml_files(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match=r"No .yaml or .yml files found"):
            load_case_dir(empty_dir)

    def test_load_directory_with_invalid_yaml(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("not: valid: case: structure: [", encoding="utf-8")
        with pytest.raises(ValueError):
            load_case_dir(tmp_path)

    def test_load_directory_with_multiple_valid_files(self, tmp_path: Path) -> None:
        # Copy the fixture and create another valid YAML
        import shutil

        dest1 = tmp_path / "case1.yaml"
        dest2 = tmp_path / "case2.yaml"
        shutil.copy2(FIXTURE_PATH, dest1)
        shutil.copy2(FIXTURE_PATH, dest2)

        cases = load_case_dir(tmp_path)
        assert len(cases) == 2


class TestInvalidYaml:
    def test_invalid_yaml_content(self, tmp_path: Path) -> None:
        """Test that a YAML with a list at top level raises an error."""
        bad_file = tmp_path / "bad_list.yaml"
        bad_file.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a mapping"):
            load_case(bad_file)

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Test that a YAML missing required fields fails validation."""
        bad_file = tmp_path / "missing_fields.yaml"
        bad_data = {"metadata": {"case_id": "test"}, "business": {}}
        with open(bad_file, "w") as f:
            yaml.dump(bad_data, f)
        with pytest.raises((ValueError, KeyError, TypeError)):
            load_case(bad_file)
