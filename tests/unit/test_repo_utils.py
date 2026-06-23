"""
Unit tests for scripts/repo_utils.py

Tests repository discovery, mapping, and configuration loading utilities.
Only tests real logic - no trivial dict lookups or library behavior.
"""

import json

from scripts.utils.repo_utils import (
    extract_conventions_from_context,
    get_framework,
    load_repo_test_context,
    map_components_to_repos,
)


class TestMapComponentsToRepos:
    """Test map_components_to_repos function."""

    def test_odh_test_context_overrides_fallback(self, tmp_path):
        """odh-test-context data should override fallback mapping."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        # Create context with custom org
        context_data = {"org": "custom-org", "testing": {"framework": "pytest"}}
        with open(tests_dir / "notebooks.json", "w") as f:
            json.dump(context_data, f)

        result = map_components_to_repos(["notebooks"], odh_test_context_path=str(tmp_path))
        assert result == {"notebooks": "custom-org/notebooks"}

    def test_odh_prefix_creates_alias(self, tmp_path):
        """Repos with odh- prefix should create aliases without prefix."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        context_data = {"org": "opendatahub-io"}
        with open(tests_dir / "odh-special.json", "w") as f:
            json.dump(context_data, f)

        # Map using alias (without 'odh-' prefix)
        result = map_components_to_repos(["special"], odh_test_context_path=str(tmp_path))
        assert result == {"special": "opendatahub-io/odh-special"}


class TestLoadRepoTestContext:
    """Test load_repo_test_context function."""

    def test_invalid_json_returns_none(self, tmp_path):
        """Should return None for malformed JSON without crashing."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        with open(tests_dir / "bad.json", "w") as f:
            f.write("{ invalid json }")

        result = load_repo_test_context("bad", str(tmp_path))
        assert result is None


class TestExtractConventionsFromContext:
    """Test extract_conventions_from_context function."""

    def test_extract_minimal_context_uses_defaults(self):
        """Should use default values for missing fields."""
        context = {}
        result = extract_conventions_from_context(context)

        assert result["framework"] == "unknown"
        assert result["test_file_pattern"] == "test_*.py"
        assert result["test_function_pattern"] == "test_*"
        assert result["import_style"] == "absolute"
        assert result["markers"] == []
        assert result["linting_tools"] == []


class TestGetFramework:
    """Test get_framework function."""

    def test_extracts_framework_from_context(self):
        """Should extract framework from test context."""
        context = {"testing": {"framework": "pytest"}}
        result = get_framework(test_context=context)
        assert result == "pytest"

    def test_unknown_framework_returns_none(self):
        """Should return None for 'unknown' framework (filters it out)."""
        context = {"testing": {"framework": "unknown"}}
        result = get_framework(test_context=context)
        assert result is None

    def test_no_data_returns_none(self):
        """Should return None if no data available."""
        result = get_framework()
        assert result is None
