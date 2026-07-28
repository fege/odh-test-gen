"""Shared fixtures for unit and integration tests."""

import subprocess

import pytest

from tests.constants import VALID_TC_CONTENT
from tests.helpers import write_valid_testplan


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


@pytest.fixture
def feature_dir(tmp_path):
    """A complete, valid feature directory with schema-valid frontmatter and structure."""
    write_valid_testplan(tmp_path / "TestPlan.md")
    (tmp_path / "README.md").write_text("# Test Feature\n")
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()
    (tc_dir / "INDEX.md").write_text("# Index")
    (tc_dir / "TC-API-001.md").write_text(VALID_TC_CONTENT)
    return str(tmp_path)
