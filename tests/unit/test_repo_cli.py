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


@pytest.mark.parametrize(
    "fullsend_task",
    [
        pytest.param("Run /test-plan-create-cases for the selected issue", id="command-string"),
        pytest.param('{"fixture": "scoped-task"}', id="json-object"),
        pytest.param("{}", id="empty-json-object"),
        pytest.param("not-json", id="non-json"),
        pytest.param(None, id="unset"),
    ],
)
def test_validate_local_path_allows_fullsend_artifact_descendant_when_runtime_root_matches_package(
    tmp_path, monkeypatch, fullsend_task
):
    """A matching Fullsend target root permits artifacts, regardless of task encoding."""
    workspace_root = tmp_path / "disposable-fullsend-workspace"
    skill_dir = workspace_root / "skills" / "test-plan-create-cases"
    skill_dir.mkdir(parents=True)
    feature_dir = workspace_root / "artifacts" / "test-plans" / "fixture-key" / "fixture_feature"
    feature_dir.mkdir(parents=True)
    runtime_root_alias = workspace_root / "skills" / ".."

    assert not (workspace_root / ".git").exists()
    assert list(feature_dir.iterdir()) == []
    assert runtime_root_alias.resolve() == workspace_root.resolve()
    monkeypatch.setenv("CLAUDE_SKILL_DIR", str(skill_dir))
    monkeypatch.setenv("FULLSEND_TARGET_REPO_DIR", str(runtime_root_alias))
    if fullsend_task is None:
        monkeypatch.delenv("FULLSEND_TASK", raising=False)
    else:
        monkeypatch.setenv("FULLSEND_TASK", fullsend_task)
    monkeypatch.setattr(sys, "argv", ["repo.py", "validate-local-path", str(feature_dir)])

    assert repo.main() == 0


@pytest.mark.parametrize("runtime_root_mode", ["unset", "different"], ids=["unset", "different-root"])
def test_validate_local_path_blocks_fullsend_artifact_descendant_without_matching_runtime_root(
    tmp_path, monkeypatch, runtime_root_mode
):
    """A task payload alone does not permit writes into package artifacts."""
    workspace_root = tmp_path / "disposable-fullsend-workspace"
    skill_dir = workspace_root / "skills" / "test-plan-create-cases"
    skill_dir.mkdir(parents=True)
    feature_dir = workspace_root / "artifacts" / "test-plans" / "fixture-key" / "fixture_feature"
    feature_dir.mkdir(parents=True)

    assert not (workspace_root / ".git").exists()
    monkeypatch.setenv("CLAUDE_SKILL_DIR", str(skill_dir))
    monkeypatch.setenv("FULLSEND_TASK", json.dumps({"fixture": "scoped-task"}))
    if runtime_root_mode == "unset":
        monkeypatch.delenv("FULLSEND_TARGET_REPO_DIR", raising=False)
    else:
        other_runtime_root = tmp_path / "different-fullsend-workspace"
        other_runtime_root.mkdir()
        monkeypatch.setenv("FULLSEND_TARGET_REPO_DIR", str(other_runtime_root))
    monkeypatch.setattr(sys, "argv", ["repo.py", "validate-local-path", str(feature_dir)])

    assert repo.main() == 1


@pytest.mark.parametrize(
    "protected_path",
    ["", "scripts/repo.py", "artifacts"],
    ids=["package-root", "package-source", "artifacts-root"],
)
def test_validate_local_path_still_blocks_package_source_and_artifacts_root(tmp_path, monkeypatch, protected_path):
    """A matching Fullsend root only allows descendants beneath the artifacts root."""
    workspace_root = tmp_path / "disposable-fullsend-workspace"
    skill_dir = workspace_root / "skills" / "test-plan-create-cases"
    skill_dir.mkdir(parents=True)
    (workspace_root / "scripts").mkdir()
    (workspace_root / "scripts" / "repo.py").touch()
    artifacts_root = workspace_root / "artifacts"
    artifacts_root.mkdir()
    path = workspace_root / protected_path if protected_path else workspace_root

    assert not (workspace_root / ".git").exists()
    monkeypatch.setenv("CLAUDE_SKILL_DIR", str(skill_dir))
    monkeypatch.setenv("FULLSEND_TARGET_REPO_DIR", str(workspace_root))
    monkeypatch.setenv("FULLSEND_TASK", "Run /test-plan-create-cases for the selected issue")
    monkeypatch.setattr(sys, "argv", ["repo.py", "validate-local-path", str(path)])

    assert repo.main() == 1


def test_validate_local_path_blocks_artifacts_in_gitless_plugin_without_fullsend_target(tmp_path, monkeypatch):
    """A gitless installed plugin rejects artifacts without a Fullsend target root."""
    plugin_root = tmp_path / "installed-plugin"
    skill_dir = plugin_root / "skills" / "test-plan-create-cases"
    skill_dir.mkdir(parents=True)
    feature_dir = plugin_root / "artifacts" / "test-plans" / "fixture-key" / "fixture_feature"
    feature_dir.mkdir(parents=True)

    assert not (plugin_root / ".git").exists()
    assert list(feature_dir.iterdir()) == []
    monkeypatch.setenv("CLAUDE_SKILL_DIR", str(skill_dir))
    monkeypatch.delenv("FULLSEND_TASK", raising=False)
    monkeypatch.delenv("FULLSEND_TARGET_REPO_DIR", raising=False)
    monkeypatch.setattr(sys, "argv", ["repo.py", "validate-local-path", str(feature_dir)])

    assert repo.main() == 1


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
