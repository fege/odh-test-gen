"""Shared test helper functions."""

from pathlib import Path

from scripts.utils.frontmatter_utils import write_frontmatter
from tests.constants import TESTPLAN_VALID_BODY, VALID_TEST_PLAN_DATA


def write_valid_testplan(path):
    """Write a TestPlan.md with validated frontmatter and proper structure."""
    Path(path).write_text(TESTPLAN_VALID_BODY)
    write_frontmatter(str(path), {**VALID_TEST_PLAN_DATA}, "test-plan")


def write_testplan_with_objectives(path, objectives_body):
    """Write a minimal TestPlan.md whose Section 1.3 holds the given objective lines."""
    Path(path).write_text("---\nfeature: Test\n---\n\n### 1.3 Test Objectives\n\n" + objectives_body)
    return str(path)


def add_feature(repo_path, feature_name, files):
    """Add a feature directory with specified files to a repo."""
    feature = Path(repo_path) / feature_name
    feature.mkdir(parents=True)
    for f in files:
        p = feature / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {f}\n")
