"""Unit tests for scripts/validate.py — unified validation CLI."""

import json

import pytest

from scripts.validate import validate_feature_dir, validate_gap_counts, validate_test_cases, validate_all
from scripts.utils.frontmatter_utils import write_frontmatter
from tests.constants import (
    VALID_TEST_PLAN_DATA,
    VALID_TESTPLAN_CONTENT,
    VALID_TEST_GAPS_DATA,
    VALID_TC_CONTENT,
)


@pytest.fixture
def gaps_dir(tmp_path):
    """A directory with a TestPlanGaps.md (gap_count=10)."""
    data = {**VALID_TEST_GAPS_DATA, "gap_count": 10}
    write_frontmatter(str(tmp_path / "TestPlanGaps.md"), data, "test-gaps")
    return str(tmp_path)


class TestValidateFeatureDir:
    """Tests for validate_feature_dir function."""

    def test_valid_feature_dir(self, feature_dir):
        result = json.loads(validate_feature_dir(feature_dir))

        assert result["valid"] is True
        assert result["tc_count"] == 1
        assert result["testplan_frontmatter"]["source_key"] == VALID_TEST_PLAN_DATA["source_key"]

    def test_missing_testplan(self, tmp_path):
        result = json.loads(validate_feature_dir(str(tmp_path)))

        assert result["valid"] is False
        assert "TestPlan.md not found" in result["error"]

    def test_missing_test_cases_dir(self, tmp_path):
        (tmp_path / "TestPlan.md").write_text(VALID_TESTPLAN_CONTENT)

        result = json.loads(validate_feature_dir(str(tmp_path)))

        assert result["valid"] is False
        assert "test_cases" in result["error"]

    def test_malformed_yaml_returns_json_error(self, tmp_path):
        (tmp_path / "TestPlan.md").write_text("---\n: invalid yaml: [\n---\n")
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")
        (tc_dir / "TC-API-001.md").write_text(VALID_TC_CONTENT)

        result = json.loads(validate_feature_dir(str(tmp_path)))

        assert result["valid"] is False
        assert "error" in result

    def test_no_tc_files(self, tmp_path):
        (tmp_path / "TestPlan.md").write_text(VALID_TESTPLAN_CONTENT)
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        result = json.loads(validate_feature_dir(str(tmp_path)))

        assert result["valid"] is False
        assert "No TC-*.md files found" in result["error"]


class TestValidateGapCounts:
    """Tests for validate_gap_counts function."""

    def test_valid_arithmetic(self, gaps_dir):
        result = validate_gap_counts(gaps_dir, 3, 9, 2)

        assert result["valid"] is True
        assert result["original"] == 10
        assert result["expected"] == 9

    def test_mismatch(self, gaps_dir):
        result = validate_gap_counts(gaps_dir, 3, 8, 2)

        assert result["valid"] is False
        assert result["expected"] == 9
        assert result["unresolved"] == 8

    def test_missing_file(self, tmp_path):
        result = validate_gap_counts(str(tmp_path), 0, 0, 0)

        assert result["valid"] is False
        assert "not found" in result["error"]


class TestValidateTestCases:
    """Tests for validate_test_cases function."""

    def test_valid_returns_pass(self, feature_dir):
        result = validate_test_cases(feature_dir)

        assert result["valid"] is True
        assert result["checked"] == 1
        assert result["failed"] == 0

    def test_invalid_returns_fail(self, tmp_path):
        (tmp_path / "TestPlan.md").write_text(VALID_TESTPLAN_CONTENT)
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")
        (tc_dir / "TC-API-001.md").write_text("---\ntest_case_id: TC-API-001\n---\n")

        result = validate_test_cases(str(tmp_path))

        assert result["valid"] is False
        assert result["failed"] > 0
        assert len(result["errors"]) > 0

    def test_missing_index_with_tc_files(self, tmp_path):
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "TC-API-001.md").write_text(VALID_TC_CONTENT)

        result = validate_test_cases(str(tmp_path))

        assert result["valid"] is False
        assert "INDEX.md" in result["errors"][0]["error"]

    def test_no_test_cases_dir(self, tmp_path):
        result = validate_test_cases(str(tmp_path))

        assert result["valid"] is True
        assert result["checked"] == 0


class TestValidateAll:
    """Tests for validate_all — orchestration."""

    def test_all_valid(self, tmp_path):
        write_frontmatter(str(tmp_path / "TestPlan.md"), VALID_TEST_PLAN_DATA, "test-plan")
        write_frontmatter(str(tmp_path / "TestPlanGaps.md"), {**VALID_TEST_GAPS_DATA, "gap_count": 3}, "test-gaps")
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")
        (tc_dir / "TC-API-001.md").write_text(VALID_TC_CONTENT)

        result = validate_all(str(tmp_path))

        assert result["valid"] is True
        assert len(result["frontmatter"]) == 2
        assert all(f["valid"] for f in result["frontmatter"])
        assert result["test_cases"]["valid"] is True

    def test_valid_without_test_cases(self, tmp_path):
        write_frontmatter(str(tmp_path / "TestPlan.md"), VALID_TEST_PLAN_DATA, "test-plan")

        result = validate_all(str(tmp_path))

        assert result["valid"] is True
        assert result["test_cases"]["checked"] == 0

    def test_stops_on_missing_testplan(self, tmp_path):
        result = validate_all(str(tmp_path))

        assert result["valid"] is False
        assert "TestPlan.md" in result["error"]

    def test_skips_optional_gaps(self, feature_dir):
        result = validate_all(feature_dir)

        assert result["valid"] is True
        assert len(result["frontmatter"]) == 1

    def test_reports_invalid_test_cases(self, tmp_path):
        write_frontmatter(str(tmp_path / "TestPlan.md"), VALID_TEST_PLAN_DATA, "test-plan")
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")
        (tc_dir / "TC-API-001.md").write_text("---\ntest_case_id: TC-API-001\n---\n")

        result = validate_all(str(tmp_path))

        assert result["valid"] is False
        assert result["test_cases"]["valid"] is False
