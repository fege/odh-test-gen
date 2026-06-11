"""Shared fixtures for unit and integration tests."""

import pytest

from scripts.utils.frontmatter_utils import write_frontmatter
from tests.constants import VALID_TEST_PLAN_DATA, VALID_TC_CONTENT


@pytest.fixture
def feature_dir(tmp_path):
    """A complete, valid feature directory with schema-valid frontmatter."""
    write_frontmatter(str(tmp_path / "TestPlan.md"), VALID_TEST_PLAN_DATA, "test-plan")
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()
    (tc_dir / "INDEX.md").write_text("# Index")
    (tc_dir / "TC-API-001.md").write_text(VALID_TC_CONTENT)
    return str(tmp_path)
