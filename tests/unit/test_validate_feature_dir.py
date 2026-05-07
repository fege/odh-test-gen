"""
Unit tests for scripts/validate_feature_dir.py

Tests feature directory structure validation.
"""

import json

import pytest

from scripts.validate_feature_dir import validate_feature_dir
from tests.constants import MINIMAL_TC_CONTENT, VALID_TESTPLAN_CONTENT


class TestValidateFeatureDir:
    """Test validate_feature_dir function."""

    def test_validates_complete_feature_dir(self, tmp_path):
        """Should validate a complete feature directory."""
        (tmp_path / "TestPlan.md").write_text(VALID_TESTPLAN_CONTENT)
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")
        (tc_dir / "TC-API-001.md").write_text(MINIMAL_TC_CONTENT)

        result = validate_feature_dir(str(tmp_path))
        data = json.loads(result)

        assert data['valid'] is True
        assert data['tc_count'] == 1
        assert data['testplan_frontmatter']['source_key'] == 'RHAISTRAT-1507'

    def test_fails_when_testplan_missing(self, tmp_path):
        """Should fail if TestPlan.md is missing."""
        result = validate_feature_dir(str(tmp_path))
        data = json.loads(result)

        assert data['valid'] is False
        assert 'TestPlan.md not found' in data['error']

    def test_fails_when_test_cases_dir_missing(self, tmp_path):
        """Should fail if test_cases/ directory is missing."""
        (tmp_path / "TestPlan.md").write_text(VALID_TESTPLAN_CONTENT)

        result = validate_feature_dir(str(tmp_path))
        data = json.loads(result)

        assert data['valid'] is False
        assert 'test_cases' in data['error']

    def test_fails_when_no_tc_files(self, tmp_path):
        """Should fail if no TC-*.md files exist."""
        (tmp_path / "TestPlan.md").write_text(VALID_TESTPLAN_CONTENT)
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Index")

        result = validate_feature_dir(str(tmp_path))
        data = json.loads(result)

        assert data['valid'] is False
        assert 'No TC-*.md files found' in data['error']
