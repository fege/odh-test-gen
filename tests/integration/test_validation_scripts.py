"""Integration tests for validation scripts (RHAIFIRST-277).

Tests both scripts via run_cli fixture, verifying CLI interface and JSON output.
"""

from scripts import detect_boilerplate, validate_test_scope
from tests.consts.test_plan_constants import TESTPLAN_BROAD_LEVELS, TESTPLAN_E2E_ONLY
from tests.consts.validation_constants import (
    CORE_BOILERPLATE_PATTERNS,
    CORE_SCOPE_PATTERNS,
    TESTPLAN_NO_BOILERPLATE,
    TESTPLAN_WITH_BOILERPLATE,
)
from tests.helpers import setup_validation_config


class TestValidateTestScopeCLI:
    """Integration tests for validate_test_scope.py CLI."""

    def test_valid_plan_returns_zero_violations(self, tmp_path, run_cli):
        """Valid plan outputs valid=true JSON."""
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_E2E_ONLY)

        exit_code, output = run_cli(validate_test_scope.main, [str(plan_path), f"--checks-dir={checks_dir}"])

        assert exit_code == 0
        assert output["valid"] is True
        assert len(output["violations"]) == 0

    def test_invalid_plan_detects_violations(self, tmp_path, run_cli):
        """Invalid plan outputs valid=false with violation details."""
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_BROAD_LEVELS)

        exit_code, output = run_cli(validate_test_scope.main, [str(plan_path), f"--checks-dir={checks_dir}"])

        assert exit_code == 0  # Always exit 0
        assert output["valid"] is False
        assert len(output["violations"]) > 0
        # Verify violation structure
        assert all("file" in v for v in output["violations"])
        assert all("line" in v for v in output["violations"])
        assert all("matched_pattern" in v for v in output["violations"])

    def test_cli_with_include_teams(self, tmp_path, run_cli):
        """CLI accepts --include-teams flag and merges team patterns."""
        team_config = {
            "version": "1.0",
            "allowed_test_levels": [],
            "forbidden_test_levels": ["Custom Testing"],
            "forbidden_patterns": [],
        }
        checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS, {"ai_hub": team_config})
        plan_content = TESTPLAN_E2E_ONLY.replace("UI Testing", "Custom Testing")
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        exit_code, output = run_cli(
            validate_test_scope.main, [str(plan_path), f"--checks-dir={checks_dir}", "--include-teams=ai_hub"]
        )

        assert exit_code == 0
        assert output["valid"] is False
        assert any("Custom Testing" in v["matched_pattern"] for v in output["violations"])


class TestDetectBoilerplateCLI:
    """Integration tests for detect_boilerplate.py CLI."""

    def test_valid_plan_returns_zero_violations(self, tmp_path, run_cli):
        """Valid plan outputs valid=true JSON."""
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)

        exit_code, output = run_cli(detect_boilerplate.main, [str(plan_path), f"--checks-dir={checks_dir}"])

        assert exit_code == 0
        assert output["valid"] is True
        assert output["total_violations"] == 0
        assert len(output["by_section"]) == 0

    def test_invalid_plan_detects_violations(self, tmp_path, run_cli):
        """Invalid plan outputs valid=false with violation details."""
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_WITH_BOILERPLATE)

        exit_code, output = run_cli(detect_boilerplate.main, [str(plan_path), f"--checks-dir={checks_dir}"])

        assert exit_code == 0  # Always exit 0
        assert output["valid"] is False
        assert output["total_violations"] > 0
        assert len(output["by_section"]) > 0
        # Verify violation structure
        for section_violations in output["by_section"].values():
            assert all("file" in v for v in section_violations)
            assert all("line" in v for v in section_violations)
            assert all("matched_pattern" in v for v in section_violations)
            assert all("category" in v for v in section_violations)
            assert all(v["violation_type"] == "boilerplate_phrase" for v in section_violations)

    def test_cli_with_include_teams(self, tmp_path, run_cli):
        """CLI accepts --include-teams flag and merges team patterns."""
        team_config = {
            "version": "1.0",
            "patterns": {
                "objectives": ["custom boilerplate pattern"],
                "risks": [],
                "priorities": [],
            },
        }
        checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, {"ai_hub": team_config}, config_filename="boilerplate_patterns.json"
        )
        plan_content = TESTPLAN_NO_BOILERPLATE.replace(
            "vector store registration creates catalog entry", "custom boilerplate pattern text"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(plan_content)

        exit_code, output = run_cli(
            detect_boilerplate.main, [str(plan_path), f"--checks-dir={checks_dir}", "--include-teams=ai_hub"]
        )

        assert exit_code == 0
        assert output["valid"] is False
        assert output["total_violations"] > 0


class TestBothScriptsInSequence:
    """Integration tests calling both scripts in sequence (as the skill does)."""

    def test_both_scripts_on_same_plan_valid(self, tmp_path, run_cli):
        """Both scripts run successfully on the same valid plan."""
        scope_checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)
        boilerplate_checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_NO_BOILERPLATE)  # Also has valid scope

        scope_exit, scope_output = run_cli(
            validate_test_scope.main, [str(plan_path), f"--checks-dir={scope_checks_dir}"]
        )
        boilerplate_exit, boilerplate_output = run_cli(
            detect_boilerplate.main, [str(plan_path), f"--checks-dir={boilerplate_checks_dir}"]
        )

        assert scope_exit == 0
        assert boilerplate_exit == 0
        assert scope_output["valid"] is True
        assert boilerplate_output["valid"] is True

    def test_both_scripts_on_same_plan_invalid(self, tmp_path, run_cli):
        """Both scripts detect violations on the same invalid plan."""
        scope_checks_dir = setup_validation_config(tmp_path, CORE_SCOPE_PATTERNS)
        boilerplate_checks_dir = setup_validation_config(
            tmp_path, CORE_BOILERPLATE_PATTERNS, config_filename="boilerplate_patterns.json"
        )
        plan_path = tmp_path / "TestPlan.md"
        plan_path.write_text(TESTPLAN_WITH_BOILERPLATE)

        scope_exit, scope_output = run_cli(
            validate_test_scope.main, [str(plan_path), f"--checks-dir={scope_checks_dir}"]
        )
        boilerplate_exit, boilerplate_output = run_cli(
            detect_boilerplate.main, [str(plan_path), f"--checks-dir={boilerplate_checks_dir}"]
        )

        assert scope_exit == 0
        assert boilerplate_exit == 0
        # This fixture only violates boilerplate rules, not scope rules
        assert scope_output["valid"] is True
        assert boilerplate_output["valid"] is False
        assert boilerplate_output["total_violations"] > 0
