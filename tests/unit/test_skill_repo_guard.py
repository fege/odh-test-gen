"""Tests for scripts/skill_repo_guard.sh"""

import subprocess
from pathlib import Path

import pytest


def run_bash(bash_code):
    """Run bash code with skill_repo_guard.sh sourced."""
    repo_root = Path.cwd()
    skill_dir = repo_root / ".claude" / "skills" / "test-plan.create"
    guard_script = repo_root / "scripts" / "skill_repo_guard.sh"

    script = f"""
    export CLAUDE_SKILL_DIR="{skill_dir}"
    source {guard_script}
    {bash_code}
    """

    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


class TestValidateLocalPath:
    """Tests for validate_local_path function."""

    @pytest.mark.parametrize("path,force,expected_exit_code", [
        (".", "false", 1),                      # Block skill repo
        ("/tmp/test-artifacts", "false", 0),    # Allow external path
        (".", "true", 0),                       # Force flag bypasses validation
    ])
    def test_validate_local_path(self, path, force, expected_exit_code):
        """Test validate_local_path blocks skill repo, allows external paths, and respects force flag."""
        abs_path = Path.cwd() if path == "." else path
        result = run_bash(f'validate_local_path "{abs_path}" "{force}"')

        assert result.returncode == expected_exit_code


class TestValidateRemoteRepo:
    """Tests for validate_remote_repo function."""

    @pytest.mark.parametrize("repo,should_allow", [
        (None, False),                          # Block skill repo remote (None = actual remote)
        ("fege/collection-tests", True),        # Allow different repo
    ])
    def test_validate_remote_repo(self, repo, should_allow):
        """Test validate_remote_repo blocks skill repo and allows different repos."""
        if repo is None:
            get_remote = run_bash("get_skill_repo_remote")
            repo = get_remote.stdout.strip()

        result = run_bash(f'validate_remote_repo "{repo}"')

        expected_exit_code = 0 if should_allow else 1
        assert result.returncode == expected_exit_code
