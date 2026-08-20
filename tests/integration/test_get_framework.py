"""Integration tests for scripts/get_framework.py chained with validate_target_repo.py."""

import subprocess


def test_get_framework_with_validate_target_repo_chain(tmp_path):
    """Test get_framework accepts output from validate_target_repo (org/repo format)."""
    # Create mock odh-test-context
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    context_file = tests_dir / "opendatahub-tests.json"
    context_file.write_text(
        """{
        "org": "opendatahub-io",
        "testing": {
            "framework": "pytest",
            "directories": ["tests/"]
        }
    }"""
    )

    # Simulate validate_target_repo output (org/repo format)
    validate_result = subprocess.run(
        ["uv", "run", "python", "scripts/validate_target_repo.py", "--target-repo opendatahub-io/opendatahub-tests"],
        capture_output=True,
        text=True,
        check=True,
    )

    target_repo = validate_result.stdout.strip()
    assert target_repo == "opendatahub-io/opendatahub-tests"

    # Pass org/repo to get_framework (should extract repo name)
    framework_result = subprocess.run(
        ["uv", "run", "python", "scripts/get_framework.py", target_repo, str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert framework_result.stdout.strip() == "pytest"
    assert framework_result.returncode == 0


def test_get_framework_with_repo_name_only(tmp_path):
    """Test get_framework with repo name only (no org prefix)."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    context_file = tests_dir / "odh-dashboard.json"
    context_file.write_text(
        """{
        "org": "opendatahub-io",
        "testing": {
            "framework": "playwright"
        }
    }"""
    )

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_framework.py", "odh-dashboard", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "playwright"
    assert result.returncode == 0


def test_get_framework_defaults_to_pytest_when_context_missing(tmp_path):
    """Test get_framework defaults to pytest when context file doesn't exist."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_framework.py", "opendatahub-io/nonexistent-repo", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "pytest"
    assert result.returncode == 0


def test_get_framework_with_local_path_input(tmp_path):
    """Test get_framework with local path as input (extracts repo name from path)."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    context_file = tests_dir / "opendatahub-tests.json"
    context_file.write_text(
        """{
        "org": "opendatahub-io",
        "testing": {
            "framework": "pytest"
        }
    }"""
    )

    # Simulate local path input
    local_path = "~/Code/opendatahub-tests"

    result = subprocess.run(
        ["uv", "run", "python", "scripts/get_framework.py", local_path, str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "pytest"
    assert result.returncode == 0
