"""Unit tests for scripts/detect_boilerplate.py

Tests boilerplate detection logic (functions, not CLI).
"""

import pytest

from scripts.detect_boilerplate import detect_boilerplate_violations, load_and_detect
from tests.consts.validation_constants import (
    CORE_BOILERPLATE_PATTERNS,
    TESTPLAN_NO_BOILERPLATE,
    TESTPLAN_WITH_BOILERPLATE,
    UNREADABLE_TEST_PLAN_KINDS,
)
from tests.helpers import make_unreadable_test_plan_path, setup_validation_config


# These functions will be imported from the actual implementation
# For now, tests will fail because stub doesn't implement them


class TestDetectBoilerplateViolations:
    """Tests for boilerplate violation detection logic."""

    def test_valid_plan_no_boilerplate(self, tmp_path):
        """No violations when objectives/risks/priorities are specific."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        assert violations["total_violations"] == 0
        assert len(violations["by_section"]) == 0

    @pytest.mark.parametrize(
        "boilerplate_phrase",
        [
            "works as expected",
            "works correctly",
            "test core functionality",
        ],
    )
    def test_objective_boilerplate_detected(self, tmp_path, boilerplate_phrase):
        """Flags generic objective phrases."""
        plan_content = TESTPLAN_NO_BOILERPLATE.replace(
            "Verify vector store registration creates catalog entry", f"Verify registration {boilerplate_phrase}"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        assert violations["total_violations"] > 0
        assert "1.3" in violations["by_section"]
        assert any(v["category"] == "objectives" for v in violations["by_section"]["1.3"])
        assert any(v["violation_type"] == "boilerplate_phrase" for v in violations["by_section"]["1.3"])

    def test_objective_ensure_proper_error_handling_generic(self, tmp_path):
        """Flags generic 'ensure proper error handling' without specifics."""
        plan_content = TESTPLAN_NO_BOILERPLATE.replace(
            "Verify proper error handling for invalid credentials", "Ensure proper error handling"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        assert violations["total_violations"] > 0
        assert "1.3" in violations["by_section"]

    def test_objective_specific_error_handling_allowed(self, tmp_path):
        """Allows 'ensure proper error handling for [specific case]'."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)  # Already has specific error handling

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        # Should not flag specific error handling
        assert violations["total_violations"] == 0

    def test_risk_generic_dependency_on_external_services(self, tmp_path):
        """Flags generic 'dependency on external services' without naming them."""
        plan_content = TESTPLAN_NO_BOILERPLATE.replace(
            "Dependency on external services - PostgreSQL vector database", "Dependency on external services"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        assert violations["total_violations"] > 0
        assert "8" in violations["by_section"]
        assert any(v["category"] == "risks" for v in violations["by_section"]["8"])

    def test_risk_specific_dependency_allowed(self, tmp_path):
        """Allows 'dependency on external services - [service name]'."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)  # Already has specific dependency

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        assert violations["total_violations"] == 0

    def test_priority_generic_core_functionality(self, tmp_path):
        """Flags generic 'core functionality' in priorities."""
        plan_content = TESTPLAN_NO_BOILERPLATE.replace("registration and deletion flows", "core functionality")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        assert violations["total_violations"] > 0
        assert "2.3" in violations["by_section"]
        assert any(v["category"] == "priorities" for v in violations["by_section"]["2.3"])

    def test_multiple_violations_across_sections(self, tmp_path):
        """Aggregates violations by section."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_WITH_BOILERPLATE)

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        assert violations["total_violations"] >= 5  # Multiple violations
        assert "1.3" in violations["by_section"]  # objectives
        assert "2.3" in violations["by_section"]  # priorities
        assert "8" in violations["by_section"]  # risks

    def test_case_insensitive_matching(self, tmp_path):
        """Handles case variations."""
        plan_content = TESTPLAN_NO_BOILERPLATE.replace("registration creates", "WORKS AS EXPECTED")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        assert violations["total_violations"] > 0

    def test_violation_contains_line_number_and_context(self, tmp_path):
        """Violations include line numbers and context."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_WITH_BOILERPLATE)

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        for section_violations in violations["by_section"].values():
            for v in section_violations:
                assert "line" in v
                assert isinstance(v["line"], int)
                assert v["line"] > 0
                assert "context" in v
                assert len(v["context"]) > 0
                assert v["category"] in {"objectives", "risks", "priorities"}
                assert v["violation_type"] == "boilerplate_phrase"

    def test_overlapping_patterns_on_same_line_count_once(self, tmp_path):
        """Two regexes matching the same line are one problem, not two — a sentence tripping
        both "works as expected" and "works correctly" is one generic habit, not two violations.
        """
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(
            TESTPLAN_NO_BOILERPLATE.replace(
                "Verify vector store registration creates catalog entry",
                "Verify the login works as expected and works correctly under load",
            )
        )

        violations = detect_boilerplate_violations(str(plan_path), CORE_BOILERPLATE_PATTERNS)

        objective_violations = violations["by_section"].get("1.3", [])
        assert len(objective_violations) == 1


class TestLoadAndDetect:
    """Tests for end-to-end detection with config loading."""

    def test_integration_with_config_loader(self, tmp_path):
        """Detects boilerplate using loaded config."""
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_WITH_BOILERPLATE)

        result = load_and_detect(str(plan_path), checks_dir, teams=None)

        assert result["valid"] is False
        assert result["total_violations"] > 0

    def test_valid_plan_returns_valid_true(self, tmp_path):
        """Valid plan returns valid=true."""
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)

        result = load_and_detect(str(plan_path), checks_dir, teams=None)

        assert result["valid"] is True
        assert result["total_violations"] == 0

    def test_missing_checks_dir_returns_structured_error(self, tmp_path):
        """Missing core config directory returns a JSON error instead of raising."""
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)

        result = load_and_detect(str(plan_path), str(tmp_path / "nonexistent_checks"), teams=None)

        assert result["valid"] is False
        assert "error" in result

    def test_malformed_config_returns_structured_error(self, tmp_path):
        """Invalid JSON in the core config returns a JSON error instead of raising."""
        checks_dir = tmp_path / "checks"
        (checks_dir / "core").mkdir(parents=True)
        (checks_dir / "core" / "boilerplate_patterns.json").write_text("{not valid json")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)

        result = load_and_detect(str(plan_path), str(checks_dir), teams=None)

        assert result["valid"] is False
        assert "error" in result

    def test_root_list_config_returns_structured_error(self, tmp_path):
        """A root JSON array in the core config returns a JSON error instead of raising AttributeError."""
        checks_dir = tmp_path / "checks"
        (checks_dir / "core").mkdir(parents=True)
        (checks_dir / "core" / "boilerplate_patterns.json").write_text("[]")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)

        result = load_and_detect(str(plan_path), str(checks_dir), teams=None)

        assert result["valid"] is False
        assert "error" in result
        assert isinstance(result["error"], str)
        assert result["error"]

    def test_missing_test_plan_path_returns_structured_error(self, tmp_path):
        """Missing TestPlan.md returns a JSON error instead of raising FileNotFoundError."""
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )

        result = load_and_detect(str(tmp_path / "nonexistent.md"), checks_dir, teams=None)

        assert result["valid"] is False
        assert "error" in result

    def test_invalid_regex_pattern_returns_structured_error(self, tmp_path):
        """An unparseable regex in the config returns a JSON error instead of raising re.error."""
        checks_dir = tmp_path / "checks"
        (checks_dir / "core").mkdir(parents=True)
        (checks_dir / "core" / "boilerplate_patterns.json").write_text(
            '{"version": "1.0", "patterns": {"objectives": ["(unclosed"], "risks": [], "priorities": []}}'
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)

        result = load_and_detect(str(plan_path), str(checks_dir), teams=None)

        assert result["valid"] is False
        assert "error" in result

    @pytest.mark.parametrize("kind", UNREADABLE_TEST_PLAN_KINDS)
    def test_unreadable_test_plan_path_returns_structured_error(self, tmp_path, kind):
        """Directory or non-UTF-8 test_plan_path returns JSON error, not a traceback."""
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )
        plan_path = make_unreadable_test_plan_path(tmp_path, kind)

        result = load_and_detect(plan_path, checks_dir, teams=None)

        assert result["valid"] is False
        assert "error" in result
        assert isinstance(result["error"], str)
        assert result["error"]
