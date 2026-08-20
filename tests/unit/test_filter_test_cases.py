"""
Unit tests for filter_test_cases.py — category split and re-implement merge.
"""

import json

import pytest

from scripts.filter_test_cases import apply_reimplement, filter_test_cases
from tests.helpers import write_tc


@pytest.fixture
def feature_with_implemented_ui_and_be(tmp_path):
    """Feature dir with both UI and backend TCs marked Complete."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()
    write_tc(tc_dir, "TC-E2E-001", "Complete", status="Automated")
    write_tc(tc_dir, "TC-UI-001", "Complete", status="Automated")
    write_tc(tc_dir, "TC-NEG-001", "Not Started")
    return tmp_path


@pytest.fixture
def feature_with_three_implemented(tmp_path):
    """Three implemented backend TCs plus one not-started."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()
    write_tc(tc_dir, "TC-E2E-001", "Complete", status="Automated")
    write_tc(tc_dir, "TC-E2E-002", "Complete", status="Automated")
    write_tc(tc_dir, "TC-E2E-003", "Complete", status="Automated")
    write_tc(tc_dir, "TC-NEG-001", "Not Started")
    return tmp_path


class TestFilterTestCases:
    """Core automation_status + UI category split."""

    def test_splits_be_ui_and_implemented(self, tmp_path):
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        write_tc(tc_dir, "TC-E2E-001", "Not Started")
        write_tc(tc_dir, "TC-E2E-002", "Complete", status="Automated")
        write_tc(tc_dir, "TC-UI-001", "Not Started")
        write_tc(tc_dir, "TC-UI-002", "Complete", status="Automated")

        data = json.loads(filter_test_cases(str(tmp_path), ["TC-E2E-001", "TC-E2E-002", "TC-UI-001", "TC-UI-002"]))

        assert data["be_test_cases"] == ["TC-E2E-001"]
        assert data["ui_test_cases"] == ["TC-UI-001"]
        assert data["already_implemented"] == ["TC-E2E-002", "TC-UI-002"]

    @pytest.mark.parametrize(
        "automation_status,status",
        [
            ("Complete", "Automated"),
            ("complete", "automated"),
            ("COMPLETE", "AUTOMATED"),
        ],
        ids=["title", "lower", "upper"],
    )
    def test_both_done_markers_are_required_and_case_insensitive(self, tmp_path, automation_status, status):
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        write_tc(tc_dir, "TC-E2E-001", automation_status=automation_status, status=status)

        data = json.loads(filter_test_cases(str(tmp_path), ["TC-E2E-001"]))

        assert data["already_implemented"] == ["TC-E2E-001"]
        assert data["be_test_cases"] == []

    @pytest.mark.parametrize(
        "automation_status,status",
        [
            ("Complete", "Draft"),
            ("Not Started", "Automated"),
        ],
        ids=["complete-without-automated", "automated-without-complete"],
    )
    def test_either_done_marker_alone_is_not_implemented(self, tmp_path, automation_status, status):
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        write_tc(tc_dir, "TC-E2E-001", automation_status=automation_status, status=status)

        data = json.loads(filter_test_cases(str(tmp_path), ["TC-E2E-001"]))

        assert data["already_implemented"] == []
        assert data["be_test_cases"] == ["TC-E2E-001"]

    def test_missing_tc_file_raises(self, tmp_path):
        (tmp_path / "test_cases").mkdir()

        with pytest.raises(FileNotFoundError, match="TC-MISSING-001.md not found"):
            filter_test_cases(str(tmp_path), ["TC-MISSING-001"])


class TestApplyReimplement:
    """Verify re-implement merge routes TCs back to their original category."""

    @pytest.mark.parametrize(
        "tc_id,expected_in,not_expected_in",
        [
            ("TC-UI-001", "ui_test_cases", "be_test_cases"),
            ("TC-E2E-001", "be_test_cases", "ui_test_cases"),
        ],
        ids=["re-implement-ui-goes-to-ui_test_cases", "re-implement-be-goes-to-be_test_cases"],
    )
    def test_re_implement_preserves_category(
        self, feature_with_implemented_ui_and_be, tc_id, expected_in, not_expected_in
    ):
        data = json.loads(
            filter_test_cases(str(feature_with_implemented_ui_and_be), ["TC-E2E-001", "TC-UI-001", "TC-NEG-001"])
        )
        result = apply_reimplement(data, ids=list(data["already_implemented"]))

        assert tc_id in result[expected_in]
        assert tc_id not in result[not_expected_in]
        assert tc_id not in result["already_implemented"]

    def test_empty_ids_is_a_noop(self, feature_with_implemented_ui_and_be):
        data = json.loads(
            filter_test_cases(str(feature_with_implemented_ui_and_be), ["TC-E2E-001", "TC-UI-001", "TC-NEG-001"])
        )
        result = apply_reimplement(data, ids=[])

        assert result is data
        assert "TC-E2E-001" in result["already_implemented"]
        assert "TC-UI-001" in result["already_implemented"]
        assert "TC-UI-001" not in result["ui_test_cases"]
        assert "TC-E2E-001" not in result["be_test_cases"]

    def test_re_implement_clears_already_implemented(self, feature_with_implemented_ui_and_be):
        data = json.loads(
            filter_test_cases(str(feature_with_implemented_ui_and_be), ["TC-E2E-001", "TC-UI-001", "TC-NEG-001"])
        )
        result = apply_reimplement(data, ids=list(data["already_implemented"]))

        assert result["already_implemented"] == []

    def test_not_started_tcs_unaffected_by_re_implement(self, feature_with_implemented_ui_and_be):
        data = json.loads(
            filter_test_cases(str(feature_with_implemented_ui_and_be), ["TC-E2E-001", "TC-UI-001", "TC-NEG-001"])
        )
        result = apply_reimplement(data, ids=list(data["already_implemented"]))

        assert "TC-NEG-001" in result["be_test_cases"]

    @pytest.mark.parametrize(
        "ids,expected_be,expected_implemented",
        [
            ([], ["TC-NEG-001"], ["TC-E2E-001", "TC-E2E-002", "TC-E2E-003"]),
            (["TC-E2E-002"], ["TC-NEG-001", "TC-E2E-002"], ["TC-E2E-001", "TC-E2E-003"]),
            (
                ["TC-E2E-001", "TC-E2E-002", "TC-E2E-003"],
                ["TC-NEG-001", "TC-E2E-001", "TC-E2E-002", "TC-E2E-003"],
                [],
            ),
        ],
        ids=["none", "subset", "all"],
    )
    def test_folds_selected_ids(self, feature_with_three_implemented, ids, expected_be, expected_implemented):
        data = json.loads(
            filter_test_cases(
                str(feature_with_three_implemented),
                ["TC-E2E-001", "TC-E2E-002", "TC-E2E-003", "TC-NEG-001"],
            )
        )
        result = apply_reimplement(data, ids=ids)

        assert result["be_test_cases"] == expected_be
        assert result["already_implemented"] == expected_implemented

    def test_unknown_id_raises(self, feature_with_three_implemented):
        data = json.loads(
            filter_test_cases(
                str(feature_with_three_implemented),
                ["TC-E2E-001", "TC-E2E-002", "TC-E2E-003", "TC-NEG-001"],
            )
        )
        with pytest.raises(ValueError, match="TC-E2E-999"):
            apply_reimplement(data, ids=["TC-E2E-999"])
