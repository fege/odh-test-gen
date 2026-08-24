"""Integration tests for scripts/get_component_test_dir.py."""

import subprocess

import pytest

from scripts.get_component_test_dir import (
    AmbiguousComponentTestDirError,
    get_component_test_dir,
    get_component_test_dir_for_feature,
    get_teams_for_feature,
)
from tests.helpers import write_valid_testplan


def _feature_with_components(tmp_path, components: list[str] | None, *, feature: str | None = None):
    """Feature dir with a schema-valid TestPlan.md, optionally setting components."""
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir()
    testplan = feature_dir / "TestPlan.md"
    overrides = {}
    if components is not None:
        overrides["components"] = components
    if feature is not None:
        overrides["feature"] = feature
    if overrides:
        write_valid_testplan(testplan, **overrides)
    else:
        write_valid_testplan(testplan)
    return feature_dir


def test_get_component_test_dir_with_existing_component(tmp_path):
    """Sanitized component name matches an existing tests/<name> directory."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "ai_hub").mkdir()
    (tests_dir / "model_serving").mkdir()

    feature = _feature_with_components(tmp_path, ["AI Hub"])

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", str(feature), str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "tests/ai_hub"
    assert result.returncode == 0


def test_alias_maps_when_sanitized_dir_missing(tmp_path):
    """'AI Core Dashboard' has no tests/ai_core_dashboard; map to tests/ai_hub."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "ai_hub").mkdir()

    feature = _feature_with_components(tmp_path, ["AI Core Dashboard"])

    result = get_component_test_dir_for_feature(str(feature), str(tmp_path))
    assert result == "tests/ai_hub"


def test_pipelines_alias_maps_to_pipelines_components(tmp_path):
    """'Pipelines' sanitizes to pipelines, but opendatahub-tests uses pipelines_components."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "pipelines_components").mkdir()

    assert get_component_test_dir("Pipelines", str(tmp_path)) == "tests/pipelines_components"


def test_get_component_test_dir_with_nonexistent_component(tmp_path):
    """Unknown component falls back to tests/."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    feature = _feature_with_components(tmp_path, ["Nonexistent Component"])

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", str(feature), str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "tests"
    assert result.returncode == 0


def test_empty_components_falls_back_to_tests(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    feature = _feature_with_components(tmp_path, None)

    assert get_component_test_dir_for_feature(str(feature), str(tmp_path)) == "tests"


def test_multiple_components_same_dir(tmp_path):
    """Aliases that collapse to one existing directory are unambiguous."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "ai_hub").mkdir()

    feature = _feature_with_components(tmp_path, ["AI Hub", "Model Registry"])

    assert get_component_test_dir_for_feature(str(feature), str(tmp_path)) == "tests/ai_hub"


def test_multiple_components_one_existing_dir(tmp_path):
    """Ignore components that only fall back to tests/ when another dir exists."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "model_serving").mkdir()

    feature = _feature_with_components(tmp_path, ["Model Serving", "Unknown Feature"])

    assert get_component_test_dir_for_feature(str(feature), str(tmp_path)) == "tests/model_serving"


def test_stops_at_component_dir_when_child_packages_exist(tmp_path):
    """Component mapping does not enter feature packages — that is ensure_feature_test_dir."""
    tests_dir = tmp_path / "tests"
    ai_safety = tests_dir / "ai_safety"
    ai_safety.mkdir(parents=True)
    (ai_safety / "evalhub").mkdir()
    (ai_safety / "guardrails").mkdir()
    (ai_safety / "nemo_guardrails").mkdir()

    feature = _feature_with_components(
        tmp_path,
        ["AI Safety", "AI Guardrails"],
        feature="nemo_guardrails_runtime_state_api",
    )

    assert get_component_test_dir_for_feature(str(feature), str(tmp_path)) == "tests/ai_safety"


def test_multiple_components_distinct_dirs_are_ambiguous(tmp_path):
    """Two existing directories is an error — do not silently pick the first."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "model_serving").mkdir()
    (tests_dir / "ai_hub").mkdir()

    feature = _feature_with_components(tmp_path, ["Model Serving", "AI Hub"])

    with pytest.raises(AmbiguousComponentTestDirError) as exc_info:
        get_component_test_dir_for_feature(str(feature), str(tmp_path))

    assert "tests/model_serving" in exc_info.value.dirs
    assert "tests/ai_hub" in exc_info.value.dirs

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", str(feature), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Multiple test directories" in result.stderr


def test_get_component_test_dir_with_invalid_repo_path(tmp_path):
    """Test error when target repo path doesn't exist."""
    feature = _feature_with_components(tmp_path, ["AI Hub"])

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", str(feature), "/nonexistent/path"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "does not exist" in result.stderr


def test_get_component_test_dir_invalid_args():
    """Test error when missing required arguments."""
    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Usage:" in result.stderr


def test_missing_testplan_errors(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    feature = tmp_path / "feature"
    feature.mkdir()

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", str(feature), str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "TestPlan.md not found" in result.stderr


def test_scalar_components_normalized_to_list(tmp_path):
    """components field as scalar string is normalized to single-element list."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "ai_hub").mkdir()
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir()
    testplan = feature_dir / "TestPlan.md"
    # Write malformed frontmatter with scalar components
    testplan.write_text(
        """---
source_key: RHAISTRAT-999
feature: test-feature
components: AI Hub
---

# Test Plan
"""
    )

    # Should normalize "AI Hub" to ["AI Hub"] and map correctly
    result = get_component_test_dir_for_feature(str(feature_dir), str(tmp_path))
    assert result == "tests/ai_hub"

    # CLI should also work
    cli_result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", str(feature_dir), str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert cli_result.stdout.strip() == "tests/ai_hub"


class TestGetTeamsForFeature:
    """Tests for get_teams_for_feature / the --teams-only CLI mode — the --include-teams value
    source for validate_test_scope.py/detect_boilerplate.py, used by test-plan-review/create/score.
    """

    @pytest.mark.parametrize(
        "components, expected",
        [
            pytest.param(["AI Hub"], "ai_hub", id="single-component-single-team"),
            # "Model Registry" also maps to ai_hub — deduped; sorted alphabetically.
            pytest.param(["Model Serving", "AI Hub", "Model Registry"], "ai_hub,model_serving", id="deduped-sorted"),
            pytest.param(["Nonexistent Component"], "", id="unmapped-component"),
            pytest.param(None, "", id="no-components"),
        ],
    )
    def test_get_teams_for_feature(self, tmp_path, components, expected):
        feature = _feature_with_components(tmp_path, components)

        assert get_teams_for_feature(str(feature)) == expected

    def test_missing_testplan_raises_file_not_found(self, tmp_path):
        feature = tmp_path / "feature"
        feature.mkdir()

        with pytest.raises(FileNotFoundError):
            get_teams_for_feature(str(feature))

    def test_cli_teams_only_prints_team_list(self, tmp_path):
        feature = _feature_with_components(tmp_path, ["AI Hub"])

        result = subprocess.run(
            ["uv", "run", "python", "scripts/get_component_test_dir.py", "--teams-only", str(feature)],
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.stdout.strip() == "ai_hub"

    def test_cli_teams_only_missing_testplan_errors(self, tmp_path):
        feature = tmp_path / "feature"
        feature.mkdir()

        result = subprocess.run(
            ["uv", "run", "python", "scripts/get_component_test_dir.py", "--teams-only", str(feature)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "TestPlan.md not found" in result.stderr

    @pytest.mark.parametrize(
        "extra_argv",
        [
            pytest.param([], id="missing-feature-dir"),
            pytest.param(["extra"], id="extra-trailing-arg"),
        ],
    )
    def test_cli_teams_only_wrong_arg_count_shows_teams_only_usage(self, tmp_path, extra_argv):
        """A wrong arg count while attempting --teams-only must not show the two-positional-arg
        usage text — that previously left the real problem (missing/extra feature_dir) unexplained.
        """
        feature = _feature_with_components(tmp_path, ["AI Hub"])
        argv = ["--teams-only", *([str(feature)] if extra_argv else []), *extra_argv]

        result = subprocess.run(
            ["uv", "run", "python", "scripts/get_component_test_dir.py", *argv],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 1
        assert "--teams-only <feature_dir>" in result.stderr
        assert "<target_repo_path>" not in result.stderr
