"""Unit tests for scripts/validate.py — unified validation CLI."""

import json

import pytest

from scripts.validate import (
    validate_ac_citations,
    validate_all,
    validate_feature_dir,
    validate_gap_counts,
    validate_scope,
    validate_structure,
    validate_test_cases,
)
from scripts.utils.frontmatter_utils import write_frontmatter
from tests.constants import (
    TESTPLAN_AC_CITED,
    TESTPLAN_AC_MISSING,
    TESTPLAN_BOLD_HEADINGS,
    TESTPLAN_BROAD_LEVELS,
    TESTPLAN_E2E_ONLY,
    TESTPLAN_MISSING_SECTIONS,
    TESTPLAN_NO_SECTION_13,
    TESTPLAN_NO_SECTION_21,
    VALID_TEST_GAPS_DATA,
    VALID_TEST_PLAN_DATA,
    VALID_TC_CONTENT,
    VALID_TESTPLAN_CONTENT,
)
from tests.helpers import write_valid_testplan


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
        write_valid_testplan(tmp_path / "TestPlan.md")
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
        write_valid_testplan(tmp_path / "TestPlan.md")

        result = validate_all(str(tmp_path))

        assert result["valid"] is True
        assert result["test_cases"]["checked"] == 0

    def test_stops_on_missing_testplan(self, tmp_path):
        result = validate_all(str(tmp_path))

        assert result["valid"] is False
        assert "TestPlan.md" in result["error"]

    def test_skips_optional_gaps(self, tmp_path):
        write_valid_testplan(tmp_path / "TestPlan.md")
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")
        (tc_dir / "TC-API-001.md").write_text(VALID_TC_CONTENT)

        result = validate_all(str(tmp_path))

        assert result["valid"] is True
        assert len(result["frontmatter"]) == 1

    def test_reports_invalid_test_cases(self, tmp_path):
        write_valid_testplan(tmp_path / "TestPlan.md")
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")
        (tc_dir / "TC-API-001.md").write_text("---\ntest_case_id: TC-API-001\n---\n")

        result = validate_all(str(tmp_path))

        assert result["valid"] is False
        assert result["test_cases"]["valid"] is False


class TestValidateScope:
    """Tests for validate_scope — disallowed test levels in Section 2.1."""

    def test_e2e_only_passes(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_E2E_ONLY)

        result = validate_scope(str(testplan))

        assert result["valid"] is True
        assert result["violations"] == []

    def test_disallowed_levels_fail(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_BROAD_LEVELS)

        result = validate_scope(str(testplan))

        assert result["valid"] is False
        assert len(result["violations"]) == 3
        violation_names = [v["level"] for v in result["violations"]]
        assert "API Integration Testing" in violation_names
        assert "Data Validation Testing" in violation_names
        assert "Functional Testing" in violation_names

    def test_missing_section_passes(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_NO_SECTION_21)

        result = validate_scope(str(testplan))

        assert result["valid"] is True
        assert result["violations"] == []

    def test_file_not_found(self):
        result = validate_scope("/nonexistent/TestPlan.md")

        assert result["valid"] is False
        assert "error" in result


class TestValidateAcCitations:
    """Tests for validate_ac_citations — AC citation in Section 1.3 objectives."""

    def test_all_objectives_cited_passes(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_AC_CITED)

        result = validate_ac_citations(str(testplan))

        assert result["valid"] is True
        assert result["total"] == 3
        assert result["cited"] == 3
        assert result["uncited"] == []

    def test_missing_citation_fails(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_AC_MISSING)

        result = validate_ac_citations(str(testplan))

        assert result["valid"] is False
        assert result["total"] == 3
        assert result["cited"] == 2
        assert len(result["uncited"]) == 1
        assert result["uncited"][0]["line_number"] > 0

    def test_no_section_passes(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_NO_SECTION_13)

        result = validate_ac_citations(str(testplan))

        assert result["valid"] is True
        assert result["total"] == 0

    def test_file_not_found(self):
        result = validate_ac_citations("/nonexistent/TestPlan.md")

        assert result["valid"] is False
        assert "error" in result


class TestValidateStructure:
    """Tests for validate_structure — required headings and pseudo-heading detection."""

    def test_valid_structure_passes(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        write_valid_testplan(testplan)

        result = validate_structure(str(testplan))

        assert result["valid"] is True
        assert result["missing_headings"] == []
        assert result["pseudo_headings"] == []

    def test_bold_pseudo_headings_fail(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_BOLD_HEADINGS)

        result = validate_structure(str(testplan))

        assert result["valid"] is False
        assert len(result["pseudo_headings"]) == 2
        pseudo_texts = [p["text"] for p in result["pseudo_headings"]]
        assert "**Measurement Points:**" in pseudo_texts
        assert "**Purpose:**" in pseudo_texts

    def test_missing_sections_fail(self, tmp_path):
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_MISSING_SECTIONS)

        result = validate_structure(str(testplan))

        assert result["valid"] is False
        assert "### 1.3 Test Objectives" in result["missing_headings"]
        assert "### 2.1 Test Levels" in result["missing_headings"]
        assert "## 4. Interfaces Under Test" in result["missing_headings"]

    def test_file_not_found(self):
        result = validate_structure("/nonexistent/TestPlan.md")

        assert result["valid"] is False
        assert "error" in result
