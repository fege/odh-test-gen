"""Unit tests for scripts/validate_test_scope.py

Tests scope validation logic (functions, not CLI).
"""

import pytest

from scripts.validate_test_scope import detect_scope_violations, load_and_validate
from tests.consts.test_plan_constants import TESTPLAN_BROAD_LEVELS, TESTPLAN_E2E_ONLY
from tests.consts.validation_constants import CORE_SCOPE_PATTERNS, UNREADABLE_TEST_PLAN_KINDS
from tests.helpers import make_unreadable_test_plan_path, setup_validation_config


# These functions will be imported from the actual implementation
# For now, tests will fail because stub doesn't implement them


class TestDetectScopeViolations:
    """Tests for scope violation detection logic."""

    def test_valid_plan_only_e2e_ui(self, tmp_path):
        """No violations when only E2E and UI testing are present."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_E2E_ONLY)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) == 0

    def test_forbidden_unit_testing(self, tmp_path):
        """Flags 'Unit Testing' as forbidden."""
        plan_content = TESTPLAN_E2E_ONLY.replace("E2E System Testing", "Unit Testing")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) > 0
        assert any("Unit Testing" in v["matched_pattern"] for v in violations)
        assert all(
            v["violation_type"] == "forbidden_test_level" for v in violations if "Unit Testing" in v["matched_pattern"]
        )

    @pytest.mark.parametrize(
        "forbidden_level",
        [
            "Unit Testing",
            "Integration Testing",
            "Component Testing",
        ],
    )
    def test_forbidden_test_levels(self, tmp_path, forbidden_level):
        """Flags each forbidden test level."""
        plan_content = TESTPLAN_E2E_ONLY.replace("E2E System Testing", forbidden_level)
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) > 0
        assert any(forbidden_level in v["matched_pattern"] for v in violations)

    def test_forbidden_functional_testing_standalone(self, tmp_path):
        """Flags standalone 'Functional Testing' but allows it as part of e2e."""
        plan_content = TESTPLAN_E2E_ONLY.replace("UI Testing", "Functional Testing")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) > 0
        assert any("functional" in v["matched_pattern"].lower() for v in violations)

    def test_allowed_functional_as_part_of_e2e(self, tmp_path):
        """Allows 'functional testing as part of' e2e."""
        plan_content = (
            TESTPLAN_E2E_ONLY + "\n- **E2E System Testing** — functional testing as part of end-to-end flows\n"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        # Should not flag the "functional testing as part of" phrase
        assert not any("functional testing as part of" in v["context"].lower() for v in violations)

    def test_multiple_violations(self, tmp_path):
        """Aggregates multiple violations."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_BROAD_LEVELS)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) == 3
        assert sum(1 for v in violations if v["violation_type"] == "forbidden_test_level") == 2
        assert sum(1 for v in violations if v["violation_type"] == "forbidden_pattern") == 1

    def test_exact_match_does_not_double_count_overlapping_substrings(self, tmp_path):
        """Exact bolded-name matching, not substring search."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_BROAD_LEVELS)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        api_integration_hits = [v for v in violations if v["context"].strip().startswith("- **API Integration")]
        assert len(api_integration_hits) == 1
        assert api_integration_hits[0]["matched_pattern"] == "API Integration Testing"

    def test_unrecognized_test_level_flagged(self, tmp_path):
        """A level that's neither allowed nor forbidden is flagged, not silently accepted."""
        plan_content = TESTPLAN_E2E_ONLY.replace("UI Testing", "Chaos Engineering Testing")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) == 1
        assert violations[0]["violation_type"] == "unrecognized_test_level"
        assert violations[0]["matched_pattern"] == "Chaos Engineering Testing"

    def test_unrecognized_level_not_double_flagged_with_forbidden_pattern(self, tmp_path):
        """A bolded level that also trips forbidden_patterns (e.g. standalone Functional
        Testing) is reported once, not as both forbidden_pattern and unrecognized_test_level.
        """
        plan_content = TESTPLAN_E2E_ONLY.replace("UI Testing", "Functional Testing")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) == 1
        assert violations[0]["violation_type"] == "forbidden_pattern"

    def test_empty_section_flagged(self, tmp_path):
        """Section 2.1 present but with no declared bullets is flagged, not silently valid."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(
            "---\nfeature: Test Feature\nsource_key: RHAISTRAT-400\n---\n"
            "## 2. Test Strategy\n\n### 2.1 Test Levels\n\n### 2.2 Test Types\n"
            "- **Positive Testing** — valid inputs\n"
        )

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) == 1
        assert violations[0]["violation_type"] == "no_test_levels_declared"

    def test_case_insensitive_matching(self, tmp_path):
        """Handles case variations."""
        plan_content = TESTPLAN_E2E_ONLY.replace("E2E System Testing", "unit testing")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert len(violations) > 0
        assert any("unit" in v["matched_pattern"].lower() for v in violations)

    def test_violation_contains_line_number(self, tmp_path):
        """Violations include line numbers."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_BROAD_LEVELS)

        violations = detect_scope_violations(str(plan_path), CORE_SCOPE_PATTERNS)

        assert all("line" in v for v in violations)
        assert all(isinstance(v["line"], int) for v in violations)
        assert all(v["line"] > 0 for v in violations)


class TestLoadAndValidate:
    """Tests for end-to-end validation with config loading."""

    def test_integration_with_config_loader(self, tmp_path):
        """Validates plan using loaded config."""
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_BROAD_LEVELS)

        result = load_and_validate(str(plan_path), checks_dir, teams=None)

        assert result["valid"] is False
        assert len(result["violations"]) > 0

    def test_valid_plan_returns_valid_true(self, tmp_path):
        """Valid plan returns valid=true."""
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_E2E_ONLY)

        result = load_and_validate(str(plan_path), checks_dir, teams=None)

        assert result["valid"] is True
        assert len(result["violations"]) == 0

    def test_missing_checks_dir_returns_structured_error(self, tmp_path):
        """Missing core config directory returns a JSON error instead of raising."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_E2E_ONLY)

        result = load_and_validate(str(plan_path), str(tmp_path / "nonexistent_checks"), teams=None)

        assert result["valid"] is False
        assert "error" in result

    def test_malformed_config_returns_structured_error(self, tmp_path):
        """Invalid JSON in the core config returns a JSON error instead of raising."""
        checks_dir = tmp_path / "checks"
        (checks_dir / "core").mkdir(parents=True)
        (checks_dir / "core" / "scope_patterns.json").write_text("{not valid json")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_E2E_ONLY)

        result = load_and_validate(str(plan_path), str(checks_dir), teams=None)

        assert result["valid"] is False
        assert "error" in result

    def test_root_list_config_returns_structured_error(self, tmp_path):
        """A root JSON array in the core config returns a JSON error instead of raising AttributeError."""
        checks_dir = tmp_path / "checks"
        (checks_dir / "core").mkdir(parents=True)
        (checks_dir / "core" / "scope_patterns.json").write_text("[]")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_E2E_ONLY)

        result = load_and_validate(str(plan_path), str(checks_dir), teams=None)

        assert result["valid"] is False
        assert "error" in result
        assert isinstance(result["error"], str)
        assert result["error"]

    def test_missing_test_plan_path_returns_structured_error(self, tmp_path):
        """Missing TestPlan.md returns a JSON error instead of raising FileNotFoundError."""
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)

        result = load_and_validate(str(tmp_path / "nonexistent.md"), checks_dir, teams=None)

        assert result["valid"] is False
        assert "error" in result

    def test_invalid_regex_pattern_returns_structured_error(self, tmp_path):
        """An unparseable regex in the config returns a JSON error instead of raising re.error."""
        checks_dir = tmp_path / "checks"
        (checks_dir / "core").mkdir(parents=True)
        (checks_dir / "core" / "scope_patterns.json").write_text(
            '{"version": "1.0", "allowed_test_levels": ["E2E System Testing"], '
            '"forbidden_test_levels": [], "forbidden_patterns": ["(unclosed"]}'
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_E2E_ONLY)

        result = load_and_validate(str(plan_path), str(checks_dir), teams=None)

        assert result["valid"] is False
        assert "error" in result

    @pytest.mark.parametrize("kind", UNREADABLE_TEST_PLAN_KINDS)
    def test_unreadable_test_plan_path_returns_structured_error(self, tmp_path, kind):
        """Directory or non-UTF-8 test_plan_path returns JSON error, not a traceback."""
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)
        plan_path = make_unreadable_test_plan_path(tmp_path, kind)

        result = load_and_validate(plan_path, checks_dir, teams=None)

        assert result["valid"] is False
        assert "error" in result
        assert isinstance(result["error"], str)
        assert result["error"]
