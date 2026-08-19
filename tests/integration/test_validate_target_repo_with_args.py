"""
Integration tests for argument parsing scripts.

Tests validate_target_repo.py and parse_skill_args.py CLI behavior.
"""

import subprocess
from pathlib import Path

import pytest

from scripts.get_component_test_dir import get_component_test_dir
from scripts.parse_skill_args import extract_flag_value
from scripts.utils.repo_utils import load_repo_test_context


def run_validate_target_repo(args_string: str = "") -> tuple[str, int]:
    """Run validate_target_repo.py and return (stdout, exit_code)."""
    result = subprocess.run(
        ["uv", "run", "python", "scripts/validate_target_repo.py", args_string],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    return result.stdout.strip(), result.returncode


@pytest.fixture
def fake_git_repo(tmp_path):
    """Create a fake git repository."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    return tmp_path


class TestValidateTargetRepoWithArgs:
    """Test validate_target_repo.py CLI with argument parsing."""

    @pytest.mark.parametrize(
        "args,expected_output",
        [
            ("", "opendatahub-io/opendatahub-tests"),  # No args → default
            ("feature/path --target-repo opendatahub-io/notebooks", "opendatahub-io/notebooks"),
            ("--test-cases TC-001 --target-repo opendatahub-io/model-registry", "opendatahub-io/model-registry"),
        ],
    )
    def test_parses_target_repo_from_arguments(self, args, expected_output):
        """Test --target-repo flag parsing with various argument patterns."""
        output, exit_code = run_validate_target_repo(args)

        assert exit_code == 0
        assert output == expected_output

    def test_parses_local_path(self, fake_git_repo):
        """Test that --target-repo with local path is validated."""
        args = f"feature/path --target-repo {fake_git_repo}"
        output, exit_code = run_validate_target_repo(args)

        assert exit_code == 0
        assert output == str(fake_git_repo)

    def test_rejects_invalid_repo_format(self):
        """Test that invalid repo format is rejected."""
        args = "--target-repo invalid-no-slash"
        _, exit_code = run_validate_target_repo(args)

        assert exit_code == 1


class TestParseSkillArgs:
    """Test parse_skill_args.py functions."""

    @pytest.mark.parametrize(
        "args_string,flag_name,expected",
        [
            ("~/path --test-cases TC-001,TC-002", "test-cases", "TC-001 TC-002"),
            ("path --test-cases TC-NEG-001.md,TC-E2E-001.md", "test-cases", "TC-NEG-001.md TC-E2E-001.md"),
            ("path --test-cases TC-E2E-001", "test-cases", "TC-E2E-001"),
            ("path --test-cases TC-001,TC-002 --target-repo ~/repo", "test-cases", "TC-001 TC-002"),
            ("path only", "test-cases", ""),
            ("path --target-repo ~/Code/opendatahub-tests", "target-repo", "~/Code/opendatahub-tests"),
            ("path --target-repo opendatahub-io/notebooks", "target-repo", "opendatahub-io/notebooks"),
            ("path only", "target-repo", ""),
        ],
    )
    def test_extracts_and_formats_flags(self, args_string, flag_name, expected):
        """Test flag extraction with conditional comma → space conversion."""
        value = extract_flag_value(args_string, flag_name)
        if flag_name == "test-cases" and value:
            value = value.replace(",", " ")
        assert value == expected

    def test_preserves_hyphens_in_tc_ids(self):
        """Test that hyphens in TC IDs survive extraction."""
        value = extract_flag_value("path --test-cases TC-NEG-001,TC-E2E-002", "test-cases")
        value = value.replace(",", " ")
        assert value == "TC-NEG-001 TC-E2E-002"


class TestGetComponentTestDir:
    """Test get_component_test_dir function."""

    def test_maps_to_existing_component_dir(self, tmp_path):
        """Test mapping component name to existing directory."""
        tests_dir = tmp_path / "tests" / "model_serving"
        tests_dir.mkdir(parents=True)
        result = get_component_test_dir("Model Serving", str(tmp_path))
        assert result == "tests/model_serving"

    def test_falls_back_to_tests_for_missing_component(self, tmp_path):
        """Test fallback to tests/ when component dir doesn't exist."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        result = get_component_test_dir("Nonexistent Component", str(tmp_path))
        assert result == "tests"


class TestGetFramework:
    """Test get_framework function."""

    def test_extracts_framework_from_context(self, tmp_path):
        """Test framework extraction from test context."""
        context_dir = tmp_path / "tests"
        context_dir.mkdir()
        context_file = context_dir / "opendatahub-tests.json"
        context_file.write_text('{"testing": {"framework": "pytest"}}')
        context = load_repo_test_context("opendatahub-tests", str(tmp_path))
        assert context is not None
        assert context["testing"]["framework"] == "pytest"
