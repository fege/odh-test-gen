"""
Schema validation tests for test-plan artifacts.

Tests that frontmatter data validates correctly against schema rules
for test-plan, test-case, and test-gaps artifact types. Also tests
schema type detection from filenames.
"""

import pytest

from scripts.utils.schemas import validate, apply_defaults, detect_schema_type, get_schema_yaml
from tests.constants import VALID_TEST_PLAN_DATA, VALID_TEST_CASE_DATA, VALID_TEST_GAPS_DATA


class TestSchemaDetection:
    """Test schema type detection from filenames."""

    @pytest.mark.parametrize("filename,expected_schema", [
        ("TestPlan.md", "test-plan"),
        ("tool_calling/TestPlan.md", "test-plan"),
        ("TC-API-001.md", "test-case"),
        ("test_cases/TC-UI-042.md", "test-case"),
        ("TestPlanGaps.md", "test-gaps"),
        ("feature/TestPlanGaps.md", "test-gaps"),
    ])
    def test_detect_schema_type(self, filename, expected_schema):
        """Test that schema type is correctly detected from filename."""
        result = detect_schema_type(filename)
        assert result == expected_schema, f"Expected {filename} to detect as {expected_schema}, got {result}"

    @pytest.mark.parametrize("schema_type", [
        "test-plan",
        "test-case",
        "test-gaps",
        "test-plan-review",
    ])
    def test_get_schema_yaml(self, schema_type):
        """Test that get_schema_yaml returns valid YAML for each schema type."""
        result = get_schema_yaml(schema_type)

        # Should return YAML string
        assert isinstance(result, str)
        assert len(result) > 0

        # Should have required and optional sections
        assert "required:" in result

        # Should contain schema-specific fields
        assert "source_key:" in result  # All schemas have this


class TestPlanSchemaValidation:
    """Test the test-plan schema validation rules."""

    @pytest.mark.parametrize("field_name,field_value,should_pass", [
        # source_key validation (pattern: (RHAISTRAT|RHOAIENG)-\d+)
        ("source_key", "RHAISTRAT-400", True),
        ("source_key", "RHAISTRAT-1", True),
        ("source_key", "RHOAIENG-48676", True),
        ("source_key", "RHOAIENG-1", True),
        ("source_key", "INVALID-400", False),
        ("source_key", "RHAISTRAT400", False),
        ("source_key", "RHOAIENG400", False),
        # version validation (pattern: X.Y.Z)
        ("version", "1.0.0", True),
        ("version", "10.20.30", True),
        ("version", "1.0", False),
        ("version", "v1.0.0", False),
        # status enum validation (Draft, In Review, Approved)
        ("status", "Draft", True),
        ("status", "In Review", True),
        ("status", "Approved", True),
        ("status", "Invalid", False),
        ("status", "Done", False),
    ])
    def test_field_validation(self, field_name, field_value, should_pass):
        """Test that fields match their schema patterns and rules."""
        # Start with valid base data
        data = VALID_TEST_PLAN_DATA.copy()
        # Override the field being tested
        data[field_name] = field_value

        errors = validate(data, "test-plan")

        if should_pass:
            assert errors == [], f"Expected {field_name}={field_value} to pass validation, got errors: {errors}"
        else:
            assert any(field_name in err for err in errors), \
                f"Expected {field_name}={field_value} to fail with {field_name} error, got: {errors}"

    def test_defaults_applied(self):
        """Test that optional fields get default values when missing."""
        # Data without optional fields (use only required fields from base data)
        data = VALID_TEST_PLAN_DATA.copy()

        result = apply_defaults(data, "test-plan")

        # Should add empty lists for optional fields
        assert result["reviewers"] == []
        assert result["additional_docs"] == []

        # Should preserve existing values
        assert result["feature"] == "Test Feature"
        assert result["source_key"] == "RHAISTRAT-400"

    def test_defaults_do_not_overwrite_existing_values(self):
        """Test that apply_defaults preserves user-provided values."""
        data = VALID_TEST_PLAN_DATA.copy()
        data["reviewers"] = ["alice", "bob"]

        result = apply_defaults(data, "test-plan")

        # Should NOT overwrite existing values
        assert result["reviewers"] == ["alice", "bob"]
        # Should still add other defaults
        assert result["additional_docs"] == []


class TestCaseSchemaValidation:
    """Test the test-case schema validation rules."""

    @pytest.mark.parametrize("field_name,field_value,should_pass", [
        # test_case_id validation (pattern: TC-[A-Z0-9]+-\d+)
        ("test_case_id", "TC-API-001", True),
        ("test_case_id", "TC-UI-123", True),
        ("test_case_id", "TC001", False),
        ("test_case_id", "TC-api-001", False),
        # priority enum validation (P0, P1, P2)
        ("priority", "P0", True),
        ("priority", "P1", True),
        ("priority", "P2", True),
        ("priority", "P3", False),
        ("priority", "High", False),
    ])
    def test_field_validation(self, field_name, field_value, should_pass):
        """Test that test-case fields match their schema patterns and rules."""
        # Start with valid base data
        data = VALID_TEST_CASE_DATA.copy()
        # Override the field being tested
        data[field_name] = field_value

        errors = validate(data, "test-case")

        if should_pass:
            assert errors == [], f"Expected {field_name}={field_value} to pass validation, got errors: {errors}"
        else:
            assert any(field_name in err for err in errors), \
                f"Expected {field_name}={field_value} to fail with {field_name} error, got: {errors}"


class TestGapsSchemaValidation:
    """Test the test-gaps schema validation rules."""

    @pytest.mark.parametrize("field_name,field_value,should_pass", [
        # status enum validation (Open, Partially Resolved, Resolved)
        ("status", "Open", True),
        ("status", "Partially Resolved", True),
        ("status", "Resolved", True),
        ("status", "Closed", False),
    ])
    def test_field_validation(self, field_name, field_value, should_pass):
        """Test that test-gaps fields match their schema patterns and rules."""
        # Start with valid base data
        data = VALID_TEST_GAPS_DATA.copy()
        # Override the field being tested
        data[field_name] = field_value

        errors = validate(data, "test-gaps")

        if should_pass:
            assert errors == [], f"Expected {field_name}={field_value} to pass validation, got errors: {errors}"
        else:
            assert any(field_name in err for err in errors), \
                f"Expected {field_name}={field_value} to fail with {field_name} error, got: {errors}"
