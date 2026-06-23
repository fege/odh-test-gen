"""Tests for stage_artifacts() — selective staging of test plan artifacts."""

import subprocess

import pytest

from scripts.repo import stage_artifacts
from tests.conftest import add_feature


def _staged_files(repo_path):
    """Return list of staged file paths relative to repo root."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def test_stages_required_and_skips_optional(git_repo):
    """Required files are staged; absent optional files appear in skipped_files."""
    add_feature(git_repo, "feat", ["TestPlan.md", "README.md"])

    exit_code, result = stage_artifacts(str(git_repo), "feat")

    assert exit_code == 0
    assert "feat/TestPlan.md" in result["staged_files"]
    assert "feat/README.md" in result["staged_files"]
    assert "feat/TestPlanGaps.md" in result["skipped_files"]
    assert "feat/TestPlanReview.md" in result["skipped_files"]
    staged = _staged_files(git_repo)
    assert "feat/TestPlan.md" in staged
    assert "feat/README.md" in staged


def test_stages_optional_files_when_exist(git_repo):
    """TestPlanGaps.md and TestPlanReview.md are staged when present."""
    add_feature(
        git_repo,
        "feat",
        ["TestPlan.md", "README.md", "TestPlanGaps.md", "TestPlanReview.md"],
    )

    exit_code, result = stage_artifacts(str(git_repo), "feat")

    assert exit_code == 0
    assert "feat/TestPlanGaps.md" in result["staged_files"]
    assert "feat/TestPlanReview.md" in result["staged_files"]
    staged = _staged_files(git_repo)
    assert "feat/TestPlanGaps.md" in staged
    assert "feat/TestPlanReview.md" in staged


def test_stages_test_cases_when_dir_exists(git_repo):
    """test_cases/*.md files are staged when directory exists."""
    add_feature(
        git_repo,
        "feat",
        ["TestPlan.md", "README.md", "test_cases/INDEX.md", "test_cases/TC-API-001.md"],
    )

    exit_code, result = stage_artifacts(str(git_repo), "feat")

    assert exit_code == 0
    staged = _staged_files(git_repo)
    assert "feat/test_cases/INDEX.md" in staged
    assert "feat/test_cases/TC-API-001.md" in staged


@pytest.mark.parametrize(
    "missing,present",
    [
        ("TestPlan.md", ["README.md"]),
        ("README.md", ["TestPlan.md"]),
    ],
)
def test_fails_when_required_file_missing(git_repo, missing, present):
    """Returns exit 1 with error naming the missing required file."""
    add_feature(git_repo, "feat", present)

    exit_code, result = stage_artifacts(str(git_repo), "feat")

    assert exit_code == 1
    assert missing in result["error"]
