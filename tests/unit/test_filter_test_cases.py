"""
Unit tests for scripts/filter_test_cases.py

Tests filtering logic for test case implementation status.
"""

import json
from pathlib import Path

import pytest

from scripts.filter_test_cases import filter_test_cases


class TestFilterTestCases:
    """Test filter_test_cases function."""

    def _create_tc_file(self, tc_dir, tc_id, automation_status=None):
        """Helper to create a TC file with optional automation_status."""
        status_field = ""
        if automation_status is not None:
            status_field = f"automation_status: {automation_status}"

        tc_file = tc_dir / f"{tc_id}.md"
        tc_file.write_text(f"""---
test_case_id: {tc_id}
priority: P0
{status_field}
---

## Test Steps
1. Step one
2. Step two

## Expected Results
- Result one
""")
        return tc_file

    def test_filters_not_started_cases(self, tmp_path):
        """Should include test cases with automation_status='Not Started'."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        self._create_tc_file(tc_dir, "TC-API-001", automation_status="Not Started")
        self._create_tc_file(tc_dir, "TC-API-002", automation_status="Not Started")

        result = filter_test_cases(str(tmp_path), ["TC-API-001", "TC-API-002"])
        data = json.loads(result)

        assert len(data['to_implement']) == 2
        assert "TC-API-001" in data['to_implement']
        assert "TC-API-002" in data['to_implement']
        assert len(data['already_implemented']) == 0

    def test_filters_implemented_cases(self, tmp_path):
        """Should exclude test cases with automation_status='Implemented'."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        self._create_tc_file(tc_dir, "TC-API-001", automation_status="Implemented")
        self._create_tc_file(tc_dir, "TC-API-002", automation_status="Not Started")

        result = filter_test_cases(str(tmp_path), ["TC-API-001", "TC-API-002"])
        data = json.loads(result)

        assert len(data['to_implement']) == 1
        assert "TC-API-002" in data['to_implement']
        assert len(data['already_implemented']) == 1
        assert "TC-API-001" in data['already_implemented']

    def test_handles_missing_automation_status(self, tmp_path):
        """Should include test cases without automation_status field."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        self._create_tc_file(tc_dir, "TC-API-001")  # No status

        result = filter_test_cases(str(tmp_path), ["TC-API-001"])
        data = json.loads(result)

        assert len(data['to_implement']) == 1
        assert "TC-API-001" in data['to_implement']
        assert len(data['already_implemented']) == 0

    def test_handles_mixed_statuses(self, tmp_path):
        """Should correctly separate different automation statuses."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        self._create_tc_file(tc_dir, "TC-API-001", automation_status="Implemented")
        self._create_tc_file(tc_dir, "TC-API-002", automation_status="Not Started")
        self._create_tc_file(tc_dir, "TC-API-003")  # No status
        self._create_tc_file(tc_dir, "TC-API-004", automation_status="In Progress")

        result = filter_test_cases(str(tmp_path),
                                   ["TC-API-001", "TC-API-002", "TC-API-003", "TC-API-004"])
        data = json.loads(result)

        # Only Implemented should be in already_implemented
        assert len(data['already_implemented']) == 1
        assert "TC-API-001" in data['already_implemented']

        # Others should be in to_implement
        assert len(data['to_implement']) == 3
        assert "TC-API-002" in data['to_implement']
        assert "TC-API-003" in data['to_implement']
        assert "TC-API-004" in data['to_implement']

    def test_handles_nonexistent_tc_file(self, tmp_path):
        """Should raise error if TC file doesn't exist."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        with pytest.raises(FileNotFoundError, match="TC-MISSING-001.md not found"):
            filter_test_cases(str(tmp_path), ["TC-MISSING-001"])

    def test_case_insensitive_implemented_status(self, tmp_path):
        """Should handle different cases of 'Implemented' status."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        # Test lowercase
        tc1 = tc_dir / "TC-API-001.md"
        tc1.write_text("""---
test_case_id: TC-API-001
automation_status: implemented
---
# Test
""")

        # Test uppercase
        tc2 = tc_dir / "TC-API-002.md"
        tc2.write_text("""---
test_case_id: TC-API-002
automation_status: IMPLEMENTED
---
# Test
""")

        result = filter_test_cases(str(tmp_path), ["TC-API-001", "TC-API-002"])
        data = json.loads(result)

        assert len(data['already_implemented']) == 2
        assert "TC-API-001" in data['already_implemented']
        assert "TC-API-002" in data['already_implemented']
        assert len(data['to_implement']) == 0

