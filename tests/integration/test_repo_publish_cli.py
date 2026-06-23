"""CLI smoke tests for publish-artifacts and stage subcommands."""

import sys

from scripts import repo
from tests.conftest import add_feature


def test_publish_artifacts_exits_0(git_repo):
    """publish-artifacts stages, commits, and exits 0."""
    add_feature(git_repo, "feat", ["TestPlan.md", "README.md"])
    old_argv = sys.argv
    try:
        sys.argv = ["repo.py", "publish-artifacts", str(git_repo), "feat", "test commit"]
        assert repo.main() == 0
    finally:
        sys.argv = old_argv


def test_stage_exits_0(git_repo):
    """stage exits 0 with valid feature directory."""
    add_feature(git_repo, "feat", ["TestPlan.md", "README.md"])
    old_argv = sys.argv
    try:
        sys.argv = ["repo.py", "stage", str(git_repo), "feat"]
        assert repo.main() == 0
    finally:
        sys.argv = old_argv


def test_stage_exits_1_missing_required(git_repo):
    """stage exits 1 when required files are missing."""
    add_feature(git_repo, "feat", ["TestPlan.md"])
    old_argv = sys.argv
    try:
        sys.argv = ["repo.py", "stage", str(git_repo), "feat"]
        assert repo.main() == 1
    finally:
        sys.argv = old_argv
