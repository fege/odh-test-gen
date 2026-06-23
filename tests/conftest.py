"""Shared fixtures for unit and integration tests."""

import subprocess
from pathlib import Path

import pytest

from scripts.utils.frontmatter_utils import write_frontmatter
from tests.constants import VALID_TEST_PLAN_DATA, VALID_TC_CONTENT


@pytest.fixture
def git_repo(tmp_path):
    """A git repository with an initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True, check=True)
    (tmp_path / "init.txt").write_text("init")
    subprocess.run(["git", "add", "init.txt"], cwd=tmp_path, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, capture_output=True, check=True)
    return tmp_path


def add_feature(repo_path, feature_name, files):
    """Add a feature directory with specified files to a repo."""
    feature = Path(repo_path) / feature_name
    feature.mkdir(parents=True)
    for f in files:
        p = feature / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {f}\n")


@pytest.fixture
def feature_dir(tmp_path):
    """A complete, valid feature directory with schema-valid frontmatter."""
    write_frontmatter(str(tmp_path / "TestPlan.md"), VALID_TEST_PLAN_DATA, "test-plan")
    (tmp_path / "README.md").write_text("# Test Feature\n")
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()
    (tc_dir / "INDEX.md").write_text("# Index")
    (tc_dir / "TC-API-001.md").write_text(VALID_TC_CONTENT)
    return str(tmp_path)
