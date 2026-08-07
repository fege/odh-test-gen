"""Shared fixtures for unit and integration tests."""

import json
import subprocess
import sys

import pytest

from tests.constants import VALID_TC_CONTENT
from tests.helpers import write_valid_testplan


@pytest.fixture
def run_cli(capsys):
    """Run a script's argparse main() with the given argv, returning (exit_code, parsed_json).

    Usage: exit_code, output = run_cli(scripts.parse_strat.main, ["workflow-inputs", path])
    """

    def _run(main_func, argv):
        old_argv = sys.argv
        try:
            sys.argv = [old_argv[0], *argv]
            try:
                main_func()
                exit_code = 0
            except SystemExit as exc:
                exit_code = exc.code
        finally:
            sys.argv = old_argv
        return exit_code, json.loads(capsys.readouterr().out)

    return _run


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
    (tc_dir / "TC-E2E-001.md").write_text(VALID_TC_CONTENT)
    return str(tmp_path)
