"""Shared test helper functions."""

from pathlib import Path

from scripts.utils.frontmatter_utils import write_frontmatter
from tests.constants import TESTPLAN_VALID_BODY, VALID_TEST_PLAN_DATA


def write_valid_testplan(path):
    """Write a TestPlan.md with validated frontmatter and proper structure."""
    Path(path).write_text(TESTPLAN_VALID_BODY)
    write_frontmatter(str(path), {**VALID_TEST_PLAN_DATA}, "test-plan")


def add_feature(repo_path, feature_name, files):
    """Add a feature directory with specified files to a repo."""
    feature = Path(repo_path) / feature_name
    feature.mkdir(parents=True)
    for f in files:
        p = feature / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {f}\n")
