"""Integration tests for scripts/get_component_test_dir.py."""

import subprocess

import pytest


@pytest.mark.parametrize(
    "component_name,expected_dir",
    [
        ("AI Hub", "tests/ai_hub"),
        ("Model Serving", "tests/model_serving"),
        ("Pipelines", "tests/pipelines"),
    ],
)
def test_get_component_test_dir_with_existing_component(tmp_path, component_name, expected_dir):
    """Test component directory mapping when component directory exists."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "ai_hub").mkdir()
    (tests_dir / "model_serving").mkdir()
    (tests_dir / "pipelines").mkdir()

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", component_name, str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == expected_dir
    assert result.returncode == 0


@pytest.mark.parametrize(
    "component_name",
    ["Nonexistent Component", "Unknown Feature", "Random Name"],
)
def test_get_component_test_dir_with_nonexistent_component(tmp_path, component_name):
    """Test component directory mapping falls back to tests when component doesn't exist."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", component_name, str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "tests"
    assert result.returncode == 0


def test_get_component_test_dir_with_invalid_repo_path():
    """Test error when target repo path doesn't exist."""
    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_component_test_dir.py", "AI Hub", "/nonexistent/path"],
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
