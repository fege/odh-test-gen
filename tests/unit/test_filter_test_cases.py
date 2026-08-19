"""
Unit tests for filter_test_cases.py — re-implement merge preserves UI category.
"""

from unittest.mock import patch

import pytest

from scripts.filter_test_cases import filter_and_confirm_test_cases


@pytest.fixture
def feature_with_implemented_ui_and_be(tmp_path):
    """Feature dir with both UI and backend TCs marked Implemented."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    (tc_dir / "TC-E2E-001.md").write_text("---\ntest_case_id: TC-E2E-001\nautomation_status: Implemented\n---\n")
    (tc_dir / "TC-UI-001.md").write_text("---\ntest_case_id: TC-UI-001\nautomation_status: Implemented\n---\n")
    (tc_dir / "TC-NEG-001.md").write_text("---\ntest_case_id: TC-NEG-001\nautomation_status: Not Started\n---\n")
    return tmp_path


class TestReImplementCategoryPreservation:
    """Verify re-implement merge routes TCs back to their original category."""

    @pytest.mark.parametrize(
        "confirm_response,tc_id,expected_in,not_expected_in",
        [
            (True, "TC-UI-001", "ui_test_cases", "be_test_cases"),
            (True, "TC-E2E-001", "be_test_cases", "ui_test_cases"),
            (False, "TC-UI-001", "already_implemented", "ui_test_cases"),
            (False, "TC-E2E-001", "already_implemented", "be_test_cases"),
        ],
        ids=[
            "re-implement-ui-goes-to-ui_test_cases",
            "re-implement-be-goes-to-be_test_cases",
            "decline-ui-stays-in-already_implemented",
            "decline-be-stays-in-already_implemented",
        ],
    )
    def test_re_implement_preserves_category(
        self, feature_with_implemented_ui_and_be, confirm_response, tc_id, expected_in, not_expected_in
    ):
        with patch("scripts.filter_test_cases.confirm_re_implement", return_value=confirm_response):
            result = filter_and_confirm_test_cases(str(feature_with_implemented_ui_and_be), confirm=True)

        assert tc_id in result[expected_in]
        assert tc_id not in result[not_expected_in]

    def test_re_implement_clears_already_implemented(self, feature_with_implemented_ui_and_be):
        with patch("scripts.filter_test_cases.confirm_re_implement", return_value=True):
            result = filter_and_confirm_test_cases(str(feature_with_implemented_ui_and_be), confirm=True)

        assert result["already_implemented"] == []

    def test_not_started_tcs_unaffected_by_re_implement(self, feature_with_implemented_ui_and_be):
        with patch("scripts.filter_test_cases.confirm_re_implement", return_value=True):
            result = filter_and_confirm_test_cases(str(feature_with_implemented_ui_and_be), confirm=True)

        assert "TC-NEG-001" in result["be_test_cases"]
