"""
Unit test for repo CLI - simple smoke test to ensure CLI interface is stable.
"""

import json
import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import repo
from tests.constants import TEST_SKILL_DIR


def test_find_command_basic():
    """Test that find command works and returns path."""
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        # Use generic repo name (repo-agnostic test)
        sys.argv = ["repo.py", "find", "some-repo"]
        sys.stdout = StringIO()

        with patch("scripts.repo.find_repo_in_common_locations") as mock_find:
            expected_path = "/Users/test/Code/some-repo"
            mock_find.return_value = expected_path

            # This should not raise
            try:
                repo.main()
            except SystemExit as e:
                # find command exits with 0 when found
                assert e.code == 0

            output = sys.stdout.getvalue().strip()

            mock_find.assert_called_once_with("some-repo")

            # Should print the mocked path exactly (repo-name-agnostic)
            assert output == expected_path

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_find_known_returns_json():
    """Test that find-known command returns JSON format."""
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ["repo.py", "find-known", "odh-test-context"]
        sys.stdout = StringIO()

        with patch("scripts.utils.repo_utils.find_known_repo") as mock_find:
            mock_find.return_value = (
                "/Users/test/Code/odh-test-context",
                "https://github.com/opendatahub-io/odh-test-context",
            )

            try:
                repo.main()
            except SystemExit as e:
                assert e.code == 0

            output = sys.stdout.getvalue().strip()

            # Should be valid JSON
            result = json.loads(output)
            assert "path" in result
            assert "url" in result

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_locate_feature_dir_local_path():
    """Test locate-feature-dir with local directory path."""
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ["repo.py", "locate-feature-dir", "/tmp/test-validation/mcp_catalog"]
        sys.stdout = StringIO()

        with patch("os.path.isfile") as mock_isfile:
            mock_isfile.return_value = True  # TestPlan.md exists

            try:
                repo.main()
            except SystemExit as e:
                assert e.code == 0

            output = sys.stdout.getvalue().strip()

            # Should be valid JSON
            result = json.loads(output)
            assert result["feature_dir"] == "/tmp/test-validation/mcp_catalog"
            assert result["source_type"] == "local"
            assert "repo_owner" not in result  # local paths don't have repo info

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_locate_feature_dir_github_pr():
    """Test locate-feature-dir with GitHub PR URL."""
    old_argv = sys.argv
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        sys.argv = ["repo.py", "locate-feature-dir", "https://github.com/org/repo/pull/42"]
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        with (
            patch("subprocess.run") as mock_run,
            patch("scripts.utils.repo_utils.find_repo_in_common_locations") as mock_find,
            patch("scripts.repo._find_testplan_in_repo") as mock_testplan,
        ):
            # Mock gh pr view to return branch name
            mock_run.return_value.stdout = '{"headRefName": "test-plan/RHAISTRAT-400"}'
            mock_run.return_value.returncode = 0

            # Mock repo found locally
            mock_find.return_value = "/Users/test/Code/repo"

            # Mock TestPlan.md found
            mock_testplan.return_value = "/Users/test/Code/repo/mcp_catalog"

            try:
                repo.main()
            except SystemExit as e:
                assert e.code == 0

            output = sys.stdout.getvalue().strip()

            # Should be valid JSON
            result = json.loads(output)
            assert result["source_type"] == "github"
            assert result["repo_owner"] == "org"
            assert result["repo_name"] == "repo"
            assert "feature_dir" in result

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def test_validate_local_path_allows_external():
    """Test validate-local-path allows paths outside skill repo."""
    old_argv = sys.argv
    old_env = os.environ.copy()

    try:
        os.environ["CLAUDE_SKILL_DIR"] = TEST_SKILL_DIR
        sys.argv = ["repo.py", "validate-local-path", "/tmp/test-validation"]

        exit_code = repo.main()
        assert exit_code == 0

    finally:
        sys.argv = old_argv
        os.environ.clear()
        os.environ |= old_env


def test_validate_local_path_blocks_skill_repo():
    """Test validate-local-path blocks paths inside skill repo."""
    old_argv = sys.argv
    old_stderr = sys.stderr
    old_env = os.environ.copy()

    try:
        os.environ["CLAUDE_SKILL_DIR"] = TEST_SKILL_DIR
        sys.argv = ["repo.py", "validate-local-path", str(Path.cwd())]
        sys.stderr = StringIO()

        assert repo.main() == 1

        error = sys.stderr.getvalue()
        assert "Cannot create artifacts in skill repository" in error

    finally:
        sys.argv = old_argv
        sys.stderr = old_stderr
        os.environ.clear()
        os.environ |= old_env


def test_validate_local_path_allows_fullsend_output_under_a_distinct_target_root(tmp_path, monkeypatch):
    """A separate Fullsend output workspace is writable without treating it as plugin source."""
    plugin_root = tmp_path / "installed-plugin"
    skill_dir = plugin_root / "skills" / "test-plan-create-cases"
    skill_dir.mkdir(parents=True)
    repo_script = plugin_root / "scripts" / "repo.py"
    repo_script.parent.mkdir()
    repo_script.touch()
    output_root = tmp_path / "disposable-fullsend-workspace"
    feature_dir = output_root / "artifacts" / "test-plans" / "fixture-key" / "fixture_feature"
    feature_dir.mkdir(parents=True)
    runtime_root_alias = output_root / "artifacts" / ".."

    assert not (plugin_root / ".git").exists()
    assert output_root.resolve() != plugin_root.resolve()
    assert list(feature_dir.iterdir()) == []
    assert runtime_root_alias.resolve() == output_root.resolve()
    monkeypatch.setattr(repo, "__file__", str(repo_script))
    monkeypatch.delenv("CLAUDE_SKILL_DIR", raising=False)
    monkeypatch.setenv("FULLSEND_TARGET_REPO_DIR", str(runtime_root_alias))
    monkeypatch.delenv("FULLSEND_TASK", raising=False)
    monkeypatch.setattr(sys, "argv", ["repo.py", "validate-local-path", str(feature_dir)])

    assert repo.main() == 0


@pytest.mark.parametrize(
    "protected_path",
    ["", "scripts/repo.py", "artifacts/test-plans/fixture-key/fixture_feature"],
    ids=["package-root", "package-source", "package-artifacts"],
)
def test_validate_local_path_still_blocks_package_source_and_artifacts(tmp_path, monkeypatch, protected_path):
    """A distinct Fullsend output root does not make plugin files writable."""
    plugin_root = tmp_path / "installed-plugin"
    skill_dir = plugin_root / "skills" / "test-plan-create-cases"
    skill_dir.mkdir(parents=True)
    (plugin_root / "scripts").mkdir()
    repo_script = plugin_root / "scripts" / "repo.py"
    repo_script.touch()
    (plugin_root / "artifacts" / "test-plans" / "fixture-key" / "fixture_feature").mkdir(parents=True)
    path = plugin_root / protected_path if protected_path else plugin_root
    output_root = tmp_path / "disposable-fullsend-workspace"
    output_root.mkdir()

    assert not (plugin_root / ".git").exists()
    monkeypatch.setattr(repo, "__file__", str(repo_script))
    monkeypatch.delenv("CLAUDE_SKILL_DIR", raising=False)
    monkeypatch.setenv("FULLSEND_TARGET_REPO_DIR", str(output_root))
    monkeypatch.delenv("FULLSEND_TASK", raising=False)
    monkeypatch.setattr(sys, "argv", ["repo.py", "validate-local-path", str(path)])

    assert repo.main() == 1


@pytest.mark.parametrize(
    "escape_mode",
    ["outside-path", "symlink-outside", "symlink-to-package"],
    ids=["outside-target", "symlink-escape", "symlink-into-plugin-source"],
)
def test_validate_local_path_rejects_paths_that_escape_fullsend_output_root(tmp_path, monkeypatch, escape_mode, capsys):
    plugin_root = tmp_path / "installed-plugin"
    skill_dir = plugin_root / "skills" / "test-plan-create-cases"
    skill_dir.mkdir(parents=True)
    (plugin_root / "scripts").mkdir()
    repo_script = plugin_root / "scripts" / "repo.py"
    repo_script.write_text("protected package source")
    output_root = tmp_path / "disposable-fullsend-workspace"
    output_root.mkdir()

    if escape_mode == "outside-path":
        path = tmp_path / "unmanaged-output" / "feature"
        path.parent.mkdir()
    else:
        artifacts_root = output_root / "artifacts"
        artifacts_root.mkdir()
        link = artifacts_root / "redirect"
        if escape_mode == "symlink-outside":
            destination = tmp_path / "unmanaged-output"
            destination.mkdir()
            path = link / "feature"
        else:
            destination = plugin_root
            path = link / "scripts" / "repo.py"
        link.symlink_to(destination, target_is_directory=True)

    monkeypatch.setattr(repo, "__file__", str(repo_script))
    monkeypatch.delenv("CLAUDE_SKILL_DIR", raising=False)
    monkeypatch.setenv("FULLSEND_TARGET_REPO_DIR", str(output_root))
    monkeypatch.delenv("FULLSEND_TASK", raising=False)
    monkeypatch.setattr(sys, "argv", ["repo.py", "validate-local-path", str(path)])

    assert repo.main() == 1
    assert "Output path must stay in the separate Fullsend target workspace" in capsys.readouterr().err


def test_validate_local_path_blocks_artifacts_in_gitless_plugin_without_fullsend_target(tmp_path, monkeypatch, capsys):
    """A gitless installed plugin rejects artifacts without a Fullsend target root."""
    plugin_root = tmp_path / "installed-plugin"
    skill_dir = plugin_root / "skills" / "test-plan-create-cases"
    skill_dir.mkdir(parents=True)
    repo_script = plugin_root / "scripts" / "repo.py"
    repo_script.parent.mkdir()
    repo_script.touch()
    feature_dir = plugin_root / "artifacts" / "test-plans" / "fixture-key" / "fixture_feature"
    feature_dir.mkdir(parents=True)

    assert not (plugin_root / ".git").exists()
    assert list(feature_dir.iterdir()) == []
    monkeypatch.setattr(repo, "__file__", str(repo_script))
    monkeypatch.delenv("CLAUDE_SKILL_DIR", raising=False)
    monkeypatch.delenv("FULLSEND_TASK", raising=False)
    monkeypatch.delenv("FULLSEND_TARGET_REPO_DIR", raising=False)
    monkeypatch.setattr(sys, "argv", ["repo.py", "validate-local-path", str(feature_dir)])

    assert repo.main() == 1
    assert "Cannot create artifacts in skill repository" in capsys.readouterr().err


def test_validate_remote_allows_external():
    """Test validate-remote allows repositories other than skill repo."""
    old_argv = sys.argv
    old_env = os.environ.copy()

    try:
        os.environ["CLAUDE_SKILL_DIR"] = TEST_SKILL_DIR
        # Use a neutral external repo (not the default publish target to avoid confusion)
        sys.argv = ["repo.py", "validate-remote", "example-org/external-test-repo"]

        assert repo.main() == 0

    finally:
        sys.argv = old_argv
        os.environ.clear()
        os.environ |= old_env


def test_validate_remote_blocks_skill_repo():
    """Test validate-remote blocks the skill repository."""
    old_argv = sys.argv
    old_stderr = sys.stderr
    old_env = os.environ.copy()

    try:
        os.environ["CLAUDE_SKILL_DIR"] = TEST_SKILL_DIR

        # Get actual skill repo remote
        from scripts.utils.repo_utils import get_git_remote, get_git_root

        skill_parent = Path(TEST_SKILL_DIR).parent.parent
        skill_root = get_git_root(str(skill_parent))
        skill_remote = get_git_remote(skill_root)

        sys.argv = ["repo.py", "validate-remote", skill_remote]
        sys.stderr = StringIO()

        assert repo.main() == 1

        error = sys.stderr.getvalue()
        assert "Cannot publish to skill repository" in error

    finally:
        sys.argv = old_argv
        sys.stderr = old_stderr
        os.environ.clear()
        os.environ |= old_env
