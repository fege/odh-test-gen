"""
Unit tests for scripts/map_test_files.py

Tests file organization and mapping logic for test cases.
"""

import json
from pathlib import Path

import pytest

from scripts.map_test_files import map_test_files


class TestMapTestFiles:
    """Test map_test_files function."""

    def _create_tc_file(self, tc_dir, tc_id, priority="P0", title="Test"):
        """Helper to create a TC file."""
        tc_file = tc_dir / f"{tc_id}.md"
        tc_file.write_text(f"""---
test_case_id: {tc_id}
priority: {priority}
---

## Title
{title}

## Test Steps
1. Step one
""")
        return tc_file

    def test_one_per_tc_strategy(self, tmp_path):
        """Should create one file per test case."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        self._create_tc_file(tc_dir, "TC-API-001")
        self._create_tc_file(tc_dir, "TC-API-002")

        result = map_test_files(
            str(tmp_path),
            ["TC-API-001", "TC-API-002"],
            "one-per-tc",
            "tests"
        )
        data = json.loads(result)

        # Should have 2 files
        assert len(data['file_mapping']) == 2

        # Check first file
        file1 = data['file_mapping'][0]
        assert file1['file_path'] == "tests/test_tc_api_001.py"
        assert file1['test_cases'] == ["TC-API-001"]
        assert file1['function_names'] == ["test_tc_api_001"]

        # Check second file
        file2 = data['file_mapping'][1]
        assert file2['file_path'] == "tests/test_tc_api_002.py"
        assert file2['test_cases'] == ["TC-API-002"]
        assert file2['function_names'] == ["test_tc_api_002"]

    def test_by_category_strategy(self, tmp_path):
        """Should group test cases by category."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        self._create_tc_file(tc_dir, "TC-API-001", title="Create notebook")
        self._create_tc_file(tc_dir, "TC-API-002", title="Delete notebook")
        self._create_tc_file(tc_dir, "TC-E2E-001", title="Full workflow")

        result = map_test_files(
            str(tmp_path),
            ["TC-API-001", "TC-API-002", "TC-E2E-001"],
            "by-category",
            "tests",
            feature_name="notebooks"
        )
        data = json.loads(result)

        # Should have 2 files (API, E2E)
        assert len(data['file_mapping']) == 2

        # Find API file
        api_file = next(f for f in data['file_mapping'] if 'api' in f['file_path'])
        assert api_file['file_path'] == "tests/test_api_notebooks.py"
        assert len(api_file['test_cases']) == 2
        assert "TC-API-001" in api_file['test_cases']
        assert "TC-API-002" in api_file['test_cases']
        assert "test_create_notebook" in api_file['function_names']
        assert "test_delete_notebook" in api_file['function_names']

        # Find E2E file
        e2e_file = next(f for f in data['file_mapping'] if 'e2e' in f['file_path'])
        assert e2e_file['file_path'] == "tests/test_e2e_notebooks.py"
        assert e2e_file['test_cases'] == ["TC-E2E-001"]
        assert "test_full_workflow" in e2e_file['function_names']

    def test_by_category_with_subdirs_strategy(self, tmp_path):
        """Should create category subdirectories."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        self._create_tc_file(tc_dir, "TC-API-001", title="Test API")
        self._create_tc_file(tc_dir, "TC-UNIT-001", title="Test Unit")

        result = map_test_files(
            str(tmp_path),
            ["TC-API-001", "TC-UNIT-001"],
            "by-category-with-subdirs",
            "tests",
            feature_name="notebooks"
        )
        data = json.loads(result)

        assert len(data['file_mapping']) == 2

        # Find API file (should be in subdirectory)
        api_file = next(f for f in data['file_mapping'] if 'api' in f['file_path'])
        assert api_file['file_path'] == "tests/api/test_notebooks.py"

        # Find UNIT file
        unit_file = next(f for f in data['file_mapping'] if 'unit' in f['file_path'])
        assert unit_file['file_path'] == "tests/unit/test_notebooks.py"

    def test_function_name_generation(self, tmp_path):
        """Should generate valid Python function names from TC titles."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        # Title with special characters and spaces
        self._create_tc_file(tc_dir, "TC-API-001", title="Create API with special-chars & spaces!")

        result = map_test_files(
            str(tmp_path),
            ["TC-API-001"],
            "by-category",
            "tests",
            feature_name="feature"
        )
        data = json.loads(result)

        # Function name should be valid Python identifier (snake_case, no special chars)
        func_name = data['file_mapping'][0]['function_names'][0]
        assert func_name == "test_create_api_with_special_chars_spaces"

    def test_handles_nonexistent_tc_file(self, tmp_path):
        """Should raise error if TC file doesn't exist."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        with pytest.raises(FileNotFoundError, match="TC-MISSING-001.md not found"):
            map_test_files(str(tmp_path), ["TC-MISSING-001"], "by-category", "tests")

