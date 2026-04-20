"""
Frontmatter operations tests.

Tests read, write, update, and schema detection functions for test-plan artifacts.
"""

import tempfile
from pathlib import Path

from scripts.utils.frontmatter_utils import (
    read_frontmatter,
    write_frontmatter,
    update_frontmatter,
)
from tests.constants import VALID_TEST_PLAN_DATA


class TestFrontmatterReadWrite:
    """Test read and write operations on frontmatter."""

    def test_read_write_roundtrip(self):
        """Test that write_frontmatter then read_frontmatter returns same data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "TestPlan.md"

            # Write frontmatter
            write_frontmatter(test_file, VALID_TEST_PLAN_DATA, "test-plan")

            # Read it back (returns tuple: data, body)
            read_data, body = read_frontmatter(test_file)

            # Should match original data
            assert read_data == VALID_TEST_PLAN_DATA, "Roundtrip should preserve all data"

            # Verify file has frontmatter delimiters
            content = test_file.read_text()
            assert content.startswith("---\n"), "File should start with frontmatter delimiter"
            assert "\n---\n" in content, "File should have closing frontmatter delimiter"


class TestFrontmatterUpdate:
    """Test update operations on frontmatter."""

    def test_update_preserves_existing_fields(self):
        """Test that update_frontmatter only changes specified fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "TestPlan.md"

            # Write initial frontmatter
            initial_data = VALID_TEST_PLAN_DATA.copy()
            write_frontmatter(test_file, initial_data, "test-plan")

            # Update only the version field
            updates = {"version": "2.0.0"}
            update_frontmatter(test_file, updates, "test-plan")

            # Read updated data
            updated_data, body = read_frontmatter(test_file)

            # Version should be updated
            assert updated_data["version"] == "2.0.0", "Version should be updated"

            # All other fields should be preserved
            assert updated_data["feature"] == VALID_TEST_PLAN_DATA["feature"]
            assert updated_data["source_key"] == VALID_TEST_PLAN_DATA["source_key"]
            assert updated_data["status"] == VALID_TEST_PLAN_DATA["status"]
            assert updated_data["author"] == VALID_TEST_PLAN_DATA["author"]
