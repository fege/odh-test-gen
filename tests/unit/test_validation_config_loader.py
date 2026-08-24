"""Unit tests for scripts/utils/validation_config_loader.py

Tests config loading and merging logic.
"""

import json

import pytest

from scripts.utils.validation_config_loader import load_boilerplate_patterns, load_scope_patterns
from tests.consts.validation_constants import (
    BOILERPLATE_PATTERN_CATEGORIES,
    CORE_BOILERPLATE_PATTERNS,
    CORE_SCOPE_PATTERNS,
    INVALID_LIST_STR_FIELD_IDS,
    INVALID_LIST_STR_FIELD_VALUES,
    SCOPE_LIST_FIELDS,
)
from tests.helpers import setup_validation_config


class TestLoadScopePatterns:
    """Tests for scope pattern loading and merging."""

    def test_load_core_only(self, tmp_path):
        """Load baseline patterns when no teams specified."""
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)

        result = load_scope_patterns(checks_dir, teams=None)

        assert result["version"] == "1.0"
        assert len(result["allowed_test_levels"]) == 2
        assert "E2E System Testing" in result["allowed_test_levels"]
        assert len(result["forbidden_test_levels"]) == 5
        assert "Unit Testing" in result["forbidden_test_levels"]
        assert "(?i)functional testing(?! as part of)" in result["forbidden_patterns"]

    def test_load_core_plus_teams(self, tmp_path):
        """Load and merge team patterns additively with core."""
        team_config = {
            "version": "1.0",
            "allowed_test_levels": ["Performance Testing"],
            "forbidden_test_levels": ["Component Testing"],
            "forbidden_patterns": ["custom pattern"],
        }
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS, {"ai_hub": team_config})

        result = load_scope_patterns(checks_dir, teams=["ai_hub"])

        # Additive merge
        assert "E2E System Testing" in result["allowed_test_levels"]
        assert "Performance Testing" in result["allowed_test_levels"]
        assert "Unit Testing" in result["forbidden_test_levels"]
        assert "Component Testing" in result["forbidden_test_levels"]
        assert "custom pattern" in result["forbidden_patterns"]

    def test_missing_team_folder_logs_warning(self, tmp_path, caplog):
        """Gracefully handle missing team folder."""
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)

        result = load_scope_patterns(checks_dir, teams=["nonexistent"])

        assert result["version"] == "1.0"
        assert "nonexistent" in caplog.text or "not found" in caplog.text.lower()

    def test_invalid_json_raises_error(self, tmp_path):
        """Handle JSON syntax errors gracefully."""
        checks_dir = tmp_path / "checks"
        (checks_dir / "core").mkdir(parents=True)
        (checks_dir / "core" / "scope_patterns.json").write_text("{invalid json")

        with pytest.raises((json.JSONDecodeError, ValueError)):
            load_scope_patterns(str(checks_dir))

    def test_pattern_deduplication(self, tmp_path):
        """Verify duplicate patterns from multiple sources are deduplicated."""
        team_config = {
            "version": "1.0",
            "allowed_test_levels": ["E2E System Testing", "Load Testing"],
            "forbidden_test_levels": ["Unit Testing"],
            "forbidden_patterns": ["(?i)functional testing(?! as part of)", "pattern2"],
        }
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS, {"model_serving": team_config})

        result = load_scope_patterns(checks_dir, teams=["model_serving"])

        assert result["allowed_test_levels"].count("E2E System Testing") == 1
        assert result["forbidden_test_levels"].count("Unit Testing") == 1
        assert result["forbidden_patterns"].count("(?i)functional testing(?! as part of)") == 1

    @pytest.mark.parametrize("field", SCOPE_LIST_FIELDS)
    @pytest.mark.parametrize("bad_value", INVALID_LIST_STR_FIELD_VALUES, ids=INVALID_LIST_STR_FIELD_IDS)
    def test_non_list_str_field_raises_value_error(self, tmp_path, field, bad_value):
        """String, null, or nested-list scope fields raise ValueError, not TypeError or silent split."""
        config = {
            "version": "1.0",
            "allowed_test_levels": ["E2E System Testing"],
            "forbidden_test_levels": ["Unit Testing"],
            "forbidden_patterns": ["pattern"],
        }
        config[field] = bad_value
        checks_dir = setup_validation_config(tmp_path, config)

        with pytest.raises(ValueError):
            load_scope_patterns(checks_dir)


class TestLoadBoilerplatePatterns:
    """Tests for boilerplate pattern loading and merging."""

    def test_load_core_only(self, tmp_path):
        """Load baseline patterns when no teams specified."""
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )

        result = load_boilerplate_patterns(checks_dir, teams=None)

        assert result["version"] == "1.0"
        assert "verify .* works as expected" in result["patterns"]["objectives"]
        assert len(result["patterns"]["risks"]) == 2

    def test_load_core_plus_teams(self, tmp_path):
        """Load and merge team patterns additively with core."""
        team_config = {
            "version": "1.0",
            "patterns": {"objectives": ["team objective pattern"], "risks": [], "priorities": ["team priority"]},
        }
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, {"ai_hub": team_config}, config_filename="boilerplate_patterns.json"
        )

        result = load_boilerplate_patterns(checks_dir, teams=["ai_hub"])

        assert "verify .* works as expected" in result["patterns"]["objectives"]
        assert "team objective pattern" in result["patterns"]["objectives"]
        assert "team priority" in result["patterns"]["priorities"]

    def test_missing_team_folder_logs_warning(self, tmp_path, caplog):
        """Gracefully handle missing team folder."""
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )

        result = load_boilerplate_patterns(checks_dir, teams=["nonexistent"])

        assert result["version"] == "1.0"
        assert "nonexistent" in caplog.text or "not found" in caplog.text.lower()

    @pytest.mark.parametrize("category", ["objectives", "risks", "priorities"])
    def test_pattern_deduplication_per_category(self, tmp_path, category):
        """Verify duplicate patterns are deduplicated in each category."""
        core_config = {
            "version": "1.0",
            "patterns": {k: ["dup1", "dup2"] if k == category else [] for k in ["objectives", "risks", "priorities"]},
        }
        team_config = {
            "version": "1.0",
            "patterns": {k: ["dup1", "unique"] if k == category else [] for k in ["objectives", "risks", "priorities"]},
        }
        checks_dir = setup_validation_config(
            tmp_path, core_config, {"team": team_config}, config_filename="boilerplate_patterns.json"
        )

        result = load_boilerplate_patterns(checks_dir, teams=["team"])

        assert result["patterns"][category].count("dup1") == 1
        assert "dup2" in result["patterns"][category]
        assert "unique" in result["patterns"][category]

    @pytest.mark.parametrize("category", BOILERPLATE_PATTERN_CATEGORIES)
    @pytest.mark.parametrize("bad_value", INVALID_LIST_STR_FIELD_VALUES, ids=INVALID_LIST_STR_FIELD_IDS)
    def test_non_list_str_category_raises_value_error(self, tmp_path, category, bad_value):
        """String, null, or nested-list category lists raise ValueError before merge."""
        config = {
            "version": "1.0",
            "patterns": {
                "objectives": ["verify .* works as expected"],
                "risks": ["environment instability"],
                "priorities": ["basic workflow"],
            },
        }
        config["patterns"][category] = bad_value
        checks_dir = setup_validation_config(tmp_path, config, config_filename="boilerplate_patterns.json")

        with pytest.raises(ValueError):
            load_boilerplate_patterns(checks_dir)

    @pytest.mark.parametrize("bad_value", INVALID_LIST_STR_FIELD_VALUES, ids=INVALID_LIST_STR_FIELD_IDS)
    def test_patterns_must_be_mapping_raises_value_error(self, tmp_path, bad_value):
        """Non-mapping `patterns` (string, null, nested-list) raises ValueError."""
        checks_dir = setup_validation_config(
            tmp_path, {"version": "1.0", "patterns": bad_value}, config_filename="boilerplate_patterns.json"
        )

        with pytest.raises(ValueError):
            load_boilerplate_patterns(checks_dir)
