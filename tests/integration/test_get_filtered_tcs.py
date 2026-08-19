"""
Integration tests for get_filtered_tcs.py script.

Tests the single entry point for test case filtering used by skills.
"""

import json

import pytest

from scripts.get_filtered_tcs import get_filtered_tcs


@pytest.fixture(autouse=True)
def non_interactive_mode(monkeypatch):
    """Force non-interactive mode for all tests to avoid stdin prompts."""
    monkeypatch.setenv("CLAUDE_NON_INTERACTIVE", "true")


@pytest.fixture
def feature_with_mixed_tcs(tmp_path):
    """Create a feature directory with mixed test cases (backend, UI, implemented)."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    (tc_dir / "TC-E2E-001.md").write_text("---\ntest_case_id: TC-E2E-001\nautomation_status: Not Started\n---\n")
    (tc_dir / "TC-E2E-002.md").write_text("---\ntest_case_id: TC-E2E-002\nautomation_status: Implemented\n---\n")
    (tc_dir / "TC-UI-001.md").write_text("---\ntest_case_id: TC-UI-001\nautomation_status: Not Started\n---\n")
    (tc_dir / "TC-UI-002.md").write_text("---\ntest_case_id: TC-UI-002\nautomation_status: Implemented\n---\n")
    return tmp_path


class TestGetFilteredTCs:
    """Test get_filtered_tcs function."""

    def test_auto_creates_filter_file_if_missing(self, feature_with_mixed_tcs):
        """Test that filter file is created if it doesn't exist."""
        filter_file = feature_with_mixed_tcs / ".test_cases_filter.json"
        assert not filter_file.exists()

        get_filtered_tcs(str(feature_with_mixed_tcs), "be_test_cases")

        assert filter_file.exists()

    @pytest.mark.parametrize(
        "field_name,expected",
        [
            ("be_test_cases", ["TC-E2E-001"]),
            ("ui_test_cases", ["TC-UI-001"]),
            ("already_implemented", ["TC-E2E-002", "TC-UI-002"]),
        ],
    )
    def test_returns_correct_field_values(self, feature_with_mixed_tcs, field_name, expected):
        """Test that each field returns correct TCs."""
        result = get_filtered_tcs(str(feature_with_mixed_tcs), field_name)
        assert sorted(result) == sorted(expected)

    @pytest.mark.parametrize(
        "field_name,expected",
        [
            ("be_test_cases", ["TC-E2E-001"]),
            ("ui_test_cases", ["TC-UI-001"]),
            ("already_implemented", ["TC-E2E-002", "TC-UI-002"]),
        ],
    )
    def test_ui_filtering(self, feature_with_mixed_tcs, field_name, expected):
        """Test filtering separates UI and backend test cases correctly."""
        result = get_filtered_tcs(str(feature_with_mixed_tcs), field_name)
        assert sorted(result) == sorted(expected)

    def test_ui_test_cases_not_implemented(self, tmp_path):
        """Test that TC-UI-* (not implemented) goes to ui_test_cases."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()

        (tc_dir / "TC-UI-001.md").write_text("---\ntest_case_id: TC-UI-001\nautomation_status: Not Started\n---\n")

        result = get_filtered_tcs(str(tmp_path), "ui_test_cases")
        assert result == ["TC-UI-001"]

    def test_e2e_test_cases_not_implemented(self, tmp_path):
        """Test that TC-E2E-* (not implemented) goes to be_test_cases."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()

        (tc_dir / "TC-E2E-001.md").write_text("---\ntest_case_id: TC-E2E-001\nautomation_status: Not Started\n---\n")

        result = get_filtered_tcs(str(tmp_path), "be_test_cases")
        assert result == ["TC-E2E-001"]

    def test_ui_test_cases_implemented(self, tmp_path):
        """Test that TC-UI-* (implemented) goes to already_implemented."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()

        (tc_dir / "TC-UI-001.md").write_text("---\ntest_case_id: TC-UI-001\nautomation_status: Implemented\n---\n")

        result = get_filtered_tcs(str(tmp_path), "already_implemented")
        assert result == ["TC-UI-001"]

    def test_e2e_test_cases_implemented(self, tmp_path):
        """Test that TC-E2E-* (implemented) goes to already_implemented."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()

        (tc_dir / "TC-E2E-001.md").write_text("---\ntest_case_id: TC-E2E-001\nautomation_status: Implemented\n---\n")

        result = get_filtered_tcs(str(tmp_path), "already_implemented")
        assert result == ["TC-E2E-001"]

    def test_all_ui_tcs_empty_be_test_cases(self, tmp_path):
        """Test edge case: all UI TCs → empty be_test_cases."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()

        (tc_dir / "TC-UI-001.md").write_text("---\ntest_case_id: TC-UI-001\nautomation_status: Not Started\n---\n")
        (tc_dir / "TC-UI-002.md").write_text("---\ntest_case_id: TC-UI-002\nautomation_status: Not Started\n---\n")

        result = get_filtered_tcs(str(tmp_path), "be_test_cases")
        assert result == []

    def test_reads_existing_filter_file_without_recreating(self, feature_with_mixed_tcs):
        """Test that existing filter file is used without re-filtering."""
        filter_file = feature_with_mixed_tcs / ".test_cases_filter.json"

        # Pre-create filter file with custom data
        custom_data = {
            "be_test_cases": ["TC-CUSTOM-001"],
            "ui_test_cases": [],
            "already_implemented": [],
        }
        filter_file.write_text(json.dumps(custom_data))
        original_mtime = filter_file.stat().st_mtime

        result = get_filtered_tcs(str(feature_with_mixed_tcs), "be_test_cases")

        assert result == ["TC-CUSTOM-001"]
        assert filter_file.stat().st_mtime == original_mtime

    @pytest.mark.parametrize(
        "field_name,tc_ids,expected",
        [
            ("be_test_cases", ["TC-E2E-001", "TC-E2E-999"], ["TC-E2E-001"]),  # Intersection
            ("be_test_cases", ["TC-UI-001"], []),  # No intersection
            ("already_implemented", ["TC-E2E-002"], ["TC-E2E-002"]),  # Exact match
            ("be_test_cases", ["TC-E2E-001.md"], ["TC-E2E-001"]),  # With .md extension
            ("be_test_cases", ["TC-E2E-001.md", "TC-E2E-999"], ["TC-E2E-001"]),  # Mixed
        ],
    )
    def test_filters_to_specific_tc_ids(self, feature_with_mixed_tcs, field_name, tc_ids, expected):
        """Test filtering results to specific TC IDs (intersection), with/without .md extension."""
        result = get_filtered_tcs(str(feature_with_mixed_tcs), field_name, tc_ids=tc_ids)
        assert sorted(result) == sorted(expected)

    def test_invalid_field_name_raises_error(self, feature_with_mixed_tcs):
        """Test that invalid field name raises KeyError."""
        with pytest.raises(KeyError, match="Invalid field 'invalid_field'"):
            get_filtered_tcs(str(feature_with_mixed_tcs), "invalid_field")

    @pytest.mark.parametrize(
        "tc_status,field_name,expected_count",
        [
            ("Not Started", "be_test_cases", 2),  # All not started → be_test_cases
            ("Implemented", "be_test_cases", 0),  # All implemented → empty be_test_cases
            ("Implemented", "already_implemented", 2),  # All implemented → already_implemented
        ],
    )
    def test_auto_discovers_all_tcs(self, tmp_path, tc_status, field_name, expected_count):
        """Test auto-discovery of all TCs with various statuses."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()

        (tc_dir / "TC-E2E-001.md").write_text(f"---\ntest_case_id: TC-E2E-001\nautomation_status: {tc_status}\n---\n")
        (tc_dir / "TC-E2E-002.md").write_text(f"---\ntest_case_id: TC-E2E-002\nautomation_status: {tc_status}\n---\n")

        result = get_filtered_tcs(str(tmp_path), field_name, tc_ids=None)

        assert len(result) == expected_count


class TestGetFilteredTCsEndToEnd:
    """End-to-end integration tests simulating skill usage."""

    def test_skill_workflow_get_backend_tcs(self, tmp_path):
        """Test typical skill workflow: get backend test cases for implementation."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()

        (tc_dir / "TC-E2E-001.md").write_text("---\ntest_case_id: TC-E2E-001\nautomation_status: Not Started\n---\n")
        (tc_dir / "TC-E2E-002.md").write_text("---\ntest_case_id: TC-E2E-002\nautomation_status: Not Started\n---\n")
        (tc_dir / "TC-UI-001.md").write_text("---\ntest_case_id: TC-UI-001\nautomation_status: Not Started\n---\n")
        (tc_dir / "TC-E2E-003.md").write_text("---\ntest_case_id: TC-E2E-003\nautomation_status: Implemented\n---\n")

        # Skill calls: get backend test cases
        be_tcs = get_filtered_tcs(str(tmp_path), "be_test_cases")

        assert sorted(be_tcs) == ["TC-E2E-001", "TC-E2E-002"]

        # Verify persistent file structure
        filter_file = tmp_path / ".test_cases_filter.json"
        data = json.loads(filter_file.read_text())
        assert sorted(data["be_test_cases"]) == ["TC-E2E-001", "TC-E2E-002"]
        assert data["ui_test_cases"] == ["TC-UI-001"]
        assert data["already_implemented"] == ["TC-E2E-003"]

    def test_skill_workflow_with_selective_tcs(self, tmp_path):
        """Test skill workflow with --test-cases flag (user provides specific TC IDs)."""
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()

        for i in range(1, 4):
            (tc_dir / f"TC-E2E-00{i}.md").write_text(
                f"---\ntest_case_id: TC-E2E-00{i}\nautomation_status: Not Started\n---\n"
            )

        # User provides specific TC IDs (simulates --test-cases flag)
        selected_tcs = ["TC-E2E-001", "TC-E2E-003"]
        be_tcs = get_filtered_tcs(str(tmp_path), "be_test_cases", tc_ids=selected_tcs)

        assert sorted(be_tcs) == ["TC-E2E-001", "TC-E2E-003"]
