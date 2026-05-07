"""
Unit tests for scripts/utils/text_utils.py

Tests text transformation utilities.
"""

import pytest

from scripts.utils.text_utils import sanitize_to_snake_case


class TestSanitizeToSnakeCase:
    """Test sanitize_to_snake_case function."""

    def test_simple_conversion(self):
        """Should convert simple text to snake_case."""
        assert sanitize_to_snake_case("Hello World") == "hello_world"
        assert sanitize_to_snake_case("Test Case") == "test_case"

    def test_removes_special_characters(self):
        """Should remove special characters while preserving separators."""
        assert sanitize_to_snake_case("Test & Special!") == "test_special"
        assert sanitize_to_snake_case("API (v2)") == "api_v2"

    def test_handles_separators_as_underscores(self):
        """Should convert common separators (/, -, spaces) to underscores."""
        assert sanitize_to_snake_case("Create/Update") == "create_update"
        assert sanitize_to_snake_case("multi-word-text") == "multi_word_text"
        assert sanitize_to_snake_case("test case id") == "test_case_id"
        assert sanitize_to_snake_case("a/b-c d") == "a_b_c_d"

    def test_collapses_multiple_underscores(self):
        """Should collapse multiple underscores into one."""
        assert sanitize_to_snake_case("test  with   spaces") == "test_with_spaces"
        assert sanitize_to_snake_case("test---with---dashes") == "test_with_dashes"
        assert sanitize_to_snake_case("a//b") == "a_b"

    def test_strips_leading_trailing_underscores(self):
        """Should remove leading and trailing underscores."""
        assert sanitize_to_snake_case(" leading space") == "leading_space"
        assert sanitize_to_snake_case("trailing space ") == "trailing_space"
        assert sanitize_to_snake_case("  both  ") == "both"
        assert sanitize_to_snake_case("-start") == "start"
        assert sanitize_to_snake_case("end-") == "end"

    def test_lowercases_output(self):
        """Should convert to lowercase."""
        assert sanitize_to_snake_case("UPPERCASE") == "uppercase"
        assert sanitize_to_snake_case("MixedCase") == "mixedcase"

    def test_preserves_numbers(self):
        """Should preserve numbers in the output."""
        assert sanitize_to_snake_case("Test 123") == "test_123"
        assert sanitize_to_snake_case("v2.0") == "v20"
