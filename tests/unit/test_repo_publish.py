"""Tests for publish_artifacts() — stage + check-changes + commit pipeline."""

import subprocess

from scripts.repo import publish_artifacts
from tests.conftest import add_feature


def test_publishes_successfully(git_repo):
    """Stages artifacts, commits, and returns committed=True."""
    add_feature(git_repo, "feat", ["TestPlan.md", "README.md"])

    exit_code, result = publish_artifacts(str(git_repo), "feat", "test commit")

    assert exit_code == 0
    assert result["committed"] is True
    assert result["message"] == "test commit"
    assert "feat/TestPlan.md" in result["staged_files"]
    log = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "test commit" in log.stdout


def test_no_changes_returns_committed_false(git_repo):
    """When artifacts are already committed, returns committed=False."""
    add_feature(git_repo, "feat", ["TestPlan.md", "README.md"])
    subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "already committed"], cwd=git_repo, capture_output=True, check=True)

    exit_code, result = publish_artifacts(str(git_repo), "feat", "should not commit")

    assert exit_code == 0
    assert result["committed"] is False
    assert "message" not in result
