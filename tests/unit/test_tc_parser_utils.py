"""
Unit tests for TC parser utility functions.

Tests helper functions in scripts/utils/tc_parser.py for extracting
category and title from test case files.
"""

import pytest

from scripts.utils.tc_parser import extract_category_from_tc_id, extract_title_from_tc_file
from tests.constants import (
    TC_WITH_FRONTMATTER_TITLE,
    TC_WITH_TITLE_SECTION,
    TC_WITHOUT_TITLE,
)


class TestExtractCategoryFromTcId:
    """Test extract_category_from_tc_id function."""

    def test_standard_tc_id(self):
        """Should extract category from standard TC ID format."""
        assert extract_category_from_tc_id("TC-API-001") == "api"
        assert extract_category_from_tc_id("TC-E2E-042") == "e2e"
        assert extract_category_from_tc_id("TC-UNIT-123") == "unit"

    def test_lowercase_output(self):
        """Should return lowercase category."""
        assert extract_category_from_tc_id("TC-CFG-001") == "cfg"
        assert extract_category_from_tc_id("TC-SEC-001") == "sec"

    def test_multipart_category(self):
        """Should handle multi-part categories."""
        assert extract_category_from_tc_id("TC-MULTI-WORD-001") == "multi"

    def test_invalid_format(self):
        """Should return 'other' for invalid formats."""
        assert extract_category_from_tc_id("TC001") == "other"
        assert extract_category_from_tc_id("INVALID") == "other"
        assert extract_category_from_tc_id("TC-") == "other"


class TestExtractTitleFromTcFile:
    """Test extract_title_from_tc_file function."""

    def test_extracts_from_frontmatter_title(self, tmp_path):
        """Should extract title from frontmatter if present."""
        tc_file = tmp_path / "TC-API-001.md"
        tc_file.write_text(TC_WITH_FRONTMATTER_TITLE)

        result = extract_title_from_tc_file(str(tc_file))
        assert result == "Create notebook via API"

    def test_extracts_from_title_section(self, tmp_path):
        """Should extract from ## Title section if no frontmatter title."""
        tc_file = tmp_path / "TC-API-001.md"
        tc_file.write_text(TC_WITH_TITLE_SECTION)

        result = extract_title_from_tc_file(str(tc_file))
        assert result == "Delete notebook via API"

    def test_fallback_to_test_case_id(self, tmp_path):
        """Should fallback to test_case_id if no title found."""
        tc_file = tmp_path / "TC-API-001.md"
        tc_file.write_text(TC_WITHOUT_TITLE)

        result = extract_title_from_tc_file(str(tc_file))
        assert result == "TC-API-001"
