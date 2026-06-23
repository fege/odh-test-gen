"""
Integration tests for scripts/tc_parser.py

Tests parse_tc_file with real read_frontmatter function and actual TC files.
"""

import pytest

from scripts.utils.frontmatter_utils import read_frontmatter
from scripts.utils.tc_parser import parse_tc_file
from tests.integration.constants import (
    VALID_COMPLETE_TC,
    TC_WITH_MULTILINE_ITEMS,
    TC_WITH_EMPTY_LINES,
    TC_MISSING_OBJECTIVE,
    TC_EMPTY_PRECONDITIONS,
    TC_MISSING_TEST_STEPS,
    TC_MISSING_EXPECTED_RESULTS,
    TC_WITH_OPTIONAL_SECTIONS,
    TC_WITH_BULLET_TEST_STEPS,
)


class TestParseTcFile:
    """Test parse_tc_file function - public API only."""

    def test_parse_complete_tc_file(self, tmp_path):
        """Should parse complete TC file with all sections."""
        tc_file = tmp_path / "TC-API-001.md"
        tc_file.write_text(VALID_COMPLETE_TC)

        result = parse_tc_file(str(tc_file), read_frontmatter)

        # Frontmatter
        assert result["test_case_id"] == "TC-API-001"
        assert result["priority"] == "P0"

        # Mandatory sections
        assert result["objective"] == "Verify that the API returns correct metadata"
        assert len(result["preconditions"]) == 2
        assert result["preconditions"][0] == "RHOAI cluster deployed"
        assert len(result["test_steps"]) == 3
        assert result["test_steps"][0] == "Send GET request to API endpoint"
        assert len(result["expected_results"]) == 2
        assert result["expected_results"][0] == "Response status is 200"

        # Body has only optional sections
        assert "Test Data" in result["body"]
        assert "Notes" in result["body"]
        # Should NOT duplicate mandatory sections
        assert "Preconditions" not in result["body"]

    def test_multiline_items_joined_correctly(self, tmp_path):
        """Should join multi-line bullet and numbered items."""
        tc_file = tmp_path / "TC.md"
        tc_file.write_text(TC_WITH_MULTILINE_ITEMS)

        result = parse_tc_file(str(tc_file), read_frontmatter)

        # Multi-line items should be joined with spaces
        assert result["preconditions"][0] == "Requirement that spans multiple lines with indentation"
        assert result["test_steps"][0] == "Step one that also spans multiple lines"
        assert result["expected_results"][0] == "Expected result spanning multiple lines"

    def test_empty_lines_between_items_handled(self, tmp_path):
        """Should handle empty lines between list items."""
        tc_file = tmp_path / "TC.md"
        tc_file.write_text(TC_WITH_EMPTY_LINES)

        result = parse_tc_file(str(tc_file), read_frontmatter)

        assert len(result["preconditions"]) == 3
        assert len(result["test_steps"]) == 2

    def test_missing_objective_raises_error(self, tmp_path):
        """Should raise ValueError if Objective is missing."""
        tc_file = tmp_path / "TC.md"
        tc_file.write_text(TC_MISSING_OBJECTIVE)

        with pytest.raises(ValueError, match="Missing or empty \\*\\*Objective\\*\\*"):
            parse_tc_file(str(tc_file), read_frontmatter)

    def test_empty_preconditions_raises_error(self, tmp_path):
        """Should raise ValueError if Preconditions is empty."""
        tc_file = tmp_path / "TC.md"
        tc_file.write_text(TC_EMPTY_PRECONDITIONS)

        with pytest.raises(ValueError, match="Missing or empty \\*\\*Preconditions\\*\\*"):
            parse_tc_file(str(tc_file), read_frontmatter)

    def test_missing_test_steps_raises_error(self, tmp_path):
        """Should raise ValueError if Test Steps is missing."""
        tc_file = tmp_path / "TC.md"
        tc_file.write_text(TC_MISSING_TEST_STEPS)

        with pytest.raises(ValueError, match="Missing or empty \\*\\*Test Steps\\*\\*"):
            parse_tc_file(str(tc_file), read_frontmatter)

    def test_missing_expected_results_raises_error(self, tmp_path):
        """Should raise ValueError if Expected Results is missing."""
        tc_file = tmp_path / "TC.md"
        tc_file.write_text(TC_MISSING_EXPECTED_RESULTS)

        with pytest.raises(ValueError, match="Missing or empty \\*\\*Expected Results\\*\\*"):
            parse_tc_file(str(tc_file), read_frontmatter)

    def test_optional_sections_in_body(self, tmp_path):
        """Should include optional sections in body only."""
        tc_file = tmp_path / "TC.md"
        tc_file.write_text(TC_WITH_OPTIONAL_SECTIONS)

        result = parse_tc_file(str(tc_file), read_frontmatter)

        # Optional sections should be in body
        assert "Test Data" in result["body"]
        assert '{"key": "value"}' in result["body"]
        assert "Expected Response" in result["body"]
        assert "Validation" in result["body"]
        assert "Notes" in result["body"]

        # Mandatory sections should NOT be in body
        assert "Preconditions" not in result["body"]
        assert "Test Steps" not in result["body"]

    def test_test_steps_as_bullet_list_raises_error(self, tmp_path):
        """Should raise error if Test Steps uses bullets instead of numbers."""
        tc_file = tmp_path / "TC.md"
        tc_file.write_text(TC_WITH_BULLET_TEST_STEPS)

        # Should fail because _extract_numbered_list returns empty for bullets
        with pytest.raises(ValueError, match="Missing or empty \\*\\*Test Steps\\*\\*"):
            parse_tc_file(str(tc_file), read_frontmatter)
