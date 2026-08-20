"""Integration tests for scripts/get_component_test_dir.py."""

import subprocess

import pytest

from scripts.get_component_test_dir import (
    AmbiguousComponentTestDirError,
    get_component_test_dir,
    get_component_test_dir_for_feature,
)
from tests.helpers import write_valid_testplan


def _feature_with_components(tmp_path, components: list[str] | None):
    """Feature dir with a schema-valid TestPlan.md, optionally setting components."""
    feature = tmp_path / "feature"
    feature.mkdir()
    testplan = feature / "TestPlan.md"
    if components is None:
        write_valid_testplan(testplan)
    else:
        write_valid_testplan(testplan, components=components)
    return feature


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
