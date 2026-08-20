"""
Integration tests for get_filtered_tcs.py script.

Tests the single entry point for test case filtering used by skills.
"""

import pytest

from scripts.get_filtered_tcs import decide_reimplement_next, get_filtered_tcs, main
from tests.helpers import write_tc


@pytest.fixture
def feature_with_mixed_tcs(tmp_path):
    """Create a feature directory with mixed test cases (backend, UI, implemented)."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()
    write_tc(tc_dir, "TC-E2E-001", "Not Started")
    write_tc(tc_dir, "TC-E2E-002", "Complete", status="Automated")
    write_tc(tc_dir, "TC-UI-001", "Not Started")
    write_tc(tc_dir, "TC-UI-002", "Complete", status="Automated")
    return tmp_path


class TestGetFilteredTCs:
    """Test get_filtered_tcs function."""

    def test_does_not_write_filter_file(self, feature_with_mixed_tcs):
        """Live filtering must not persist .test_cases_filter.json."""
        get_filtered_tcs(str(feature_with_mixed_tcs))
        assert not (feature_with_mixed_tcs / ".test_cases_filter.json").exists()

    def test_returns_all_three_lists(self, feature_with_mixed_tcs):
        result = get_filtered_tcs(str(feature_with_mixed_tcs))
        assert result["be_test_cases"] == ["TC-E2E-001"]
        assert result["ui_test_cases"] == ["TC-UI-001"]
        assert result["already_implemented"] == ["TC-E2E-002", "TC-UI-002"]

    def test_re_reads_updated_automation_status(self, feature_with_mixed_tcs):
        """Second call must reflect TC frontmatter changes (no stale cache)."""
        first = get_filtered_tcs(str(feature_with_mixed_tcs))
        assert "TC-E2E-001" in first["be_test_cases"]

        tc_file = feature_with_mixed_tcs / "test_cases" / "TC-E2E-001.md"
        tc_file.write_text("---\ntest_case_id: TC-E2E-001\nstatus: Automated\nautomation_status: Complete\n---\n")

        second = get_filtered_tcs(str(feature_with_mixed_tcs))
        assert "TC-E2E-001" not in second["be_test_cases"]
        assert "TC-E2E-001" in second["already_implemented"]

    @pytest.mark.parametrize(
        "tc_ids,expected_be,expected_ui,expected_implemented",
        [
            (["TC-UI-001"], [], ["TC-UI-001"], []),
            (["TC-E2E-002"], [], [], ["TC-E2E-002"]),
            (["TC-E2E-001.md"], ["TC-E2E-001"], [], []),
            (["TC-E2E-001.md TC-E2E-002 TC-UI-001"], ["TC-E2E-001"], ["TC-UI-001"], ["TC-E2E-002"]),
            (["TC-E2E-001,TC-E2E-002.md,TC-UI-001"], ["TC-E2E-001"], ["TC-UI-001"], ["TC-E2E-002"]),
        ],
        ids=["ui-only", "implemented-only", "md-suffix", "space-separated-blob", "comma-separated-blob"],
    )
    def test_filters_to_specific_tc_ids(
        self, feature_with_mixed_tcs, tc_ids, expected_be, expected_ui, expected_implemented
    ):
        """Requested IDs only — unselected TCs must not appear in already_implemented."""
        result = get_filtered_tcs(str(feature_with_mixed_tcs), tc_ids=tc_ids)
        assert result["be_test_cases"] == expected_be
        assert result["ui_test_cases"] == expected_ui
        assert result["already_implemented"] == expected_implemented

    def test_missing_requested_tc_raises(self, feature_with_mixed_tcs):
        with pytest.raises(FileNotFoundError, match="TC-E2E-999.md not found"):
            get_filtered_tcs(str(feature_with_mixed_tcs), tc_ids=["TC-E2E-001", "TC-E2E-999"])

    def test_selective_ids_do_not_include_unselected_implemented(self, feature_with_mixed_tcs):
        result = get_filtered_tcs(str(feature_with_mixed_tcs), tc_ids=["TC-E2E-001"])
        assert result["already_implemented"] == []
        assert result["be_test_cases"] == ["TC-E2E-001"]

    def test_include_implemented_folds_by_category(self, feature_with_mixed_tcs):
        result = get_filtered_tcs(str(feature_with_mixed_tcs), include_implemented=True)
        assert "TC-E2E-002" in result["be_test_cases"]
        assert "TC-UI-002" in result["ui_test_cases"]
        assert result["already_implemented"] == []

    def test_reimplement_ids_folds_subset(self, feature_with_mixed_tcs):
        result = get_filtered_tcs(str(feature_with_mixed_tcs), reimplement_ids=["TC-E2E-002"])
        assert "TC-E2E-002" in result["be_test_cases"]
        assert result["already_implemented"] == ["TC-UI-002"]
        assert "TC-UI-002" not in result["ui_test_cases"]

    def test_cannot_combine_include_implemented_and_reimplement_ids(self, feature_with_mixed_tcs):
        with pytest.raises(ValueError, match="include_implemented"):
            get_filtered_tcs(
                str(feature_with_mixed_tcs),
                include_implemented=True,
                reimplement_ids=["TC-E2E-002"],
            )

    def test_all_ui_tcs_empty_be_test_cases(self, tmp_path):
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        write_tc(tc_dir, "TC-UI-001")
        write_tc(tc_dir, "TC-UI-002")

        result = get_filtered_tcs(str(tmp_path))
        assert result["be_test_cases"] == []
        assert result["ui_test_cases"] == ["TC-UI-001", "TC-UI-002"]


class TestGetFilteredTCsEndToEnd:
    """End-to-end integration tests simulating skill usage."""

    def test_skill_workflow_get_backend_tcs(self, tmp_path):
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        write_tc(tc_dir, "TC-E2E-001")
        write_tc(tc_dir, "TC-E2E-002")
        write_tc(tc_dir, "TC-UI-001")
        write_tc(tc_dir, "TC-E2E-003", "Complete", status="Automated")

        result = get_filtered_tcs(str(tmp_path))

        assert sorted(result["be_test_cases"]) == ["TC-E2E-001", "TC-E2E-002"]
        assert result["ui_test_cases"] == ["TC-UI-001"]
        assert result["already_implemented"] == ["TC-E2E-003"]

    def test_skill_workflow_with_selective_tcs(self, tmp_path):
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        for i in range(1, 4):
            write_tc(tc_dir, f"TC-E2E-00{i}")

        result = get_filtered_tcs(str(tmp_path), tc_ids=["TC-E2E-001", "TC-E2E-003"])

        assert sorted(result["be_test_cases"]) == ["TC-E2E-001", "TC-E2E-003"]


class TestGetFilteredTCsCLI:
    """CLI prints JSON and honors --include-implemented / --reimplement-ids."""

    @pytest.mark.parametrize(
        "ids_arg",
        [
            "TC-E2E-001.md TC-E2E-002 TC-UI-001",
            "TC-E2E-001,TC-E2E-002.md,TC-UI-001",
            "TC-E2E-001, TC-E2E-002, TC-UI-001.md",
        ],
        ids=["spaces", "commas", "comma-space"],
    )
    def test_cli_splits_ids_passed_as_one_arg(self, feature_with_mixed_tcs, run_cli, ids_arg):
        """parse_skill_args emits spaces; the agent often passes them as a single argv."""
        exit_code, data = run_cli(main, [str(feature_with_mixed_tcs), ids_arg])
        assert exit_code == 0
        assert data["be_test_cases"] == ["TC-E2E-001"]
        assert data["already_implemented"] == ["TC-E2E-002"]
        assert data["ui_test_cases"] == ["TC-UI-001"]

    def test_cli_prints_json(self, feature_with_mixed_tcs, run_cli):
        exit_code, data = run_cli(main, [str(feature_with_mixed_tcs)])
        assert exit_code == 0
        assert data["be_test_cases"] == ["TC-E2E-001"]
        assert data["ui_test_cases"] == ["TC-UI-001"]
        assert data["already_implemented"] == ["TC-E2E-002", "TC-UI-002"]

    def test_cli_include_implemented(self, feature_with_mixed_tcs, run_cli):
        exit_code, data = run_cli(main, [str(feature_with_mixed_tcs), "--include-implemented"])
        assert exit_code == 0
        assert "TC-E2E-002" in data["be_test_cases"]
        assert "TC-UI-002" in data["ui_test_cases"]
        assert data["already_implemented"] == []

    def test_cli_reimplement_ids_subset(self, feature_with_mixed_tcs, run_cli):
        exit_code, data = run_cli(main, [str(feature_with_mixed_tcs), "--reimplement-ids", "TC-E2E-002"])
        assert exit_code == 0
        assert "TC-E2E-002" in data["be_test_cases"]
        assert data["already_implemented"] == ["TC-UI-002"]

    def test_cli_next_prompt_user_when_interactive(self, feature_with_mixed_tcs, run_cli, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("CLAUDE_NON_INTERACTIVE", raising=False)
        exit_code, data = run_cli(main, [str(feature_with_mixed_tcs)])
        assert exit_code == 0
        assert data["next"] == "prompt_user"

    def test_cli_next_proceed_when_non_interactive(self, feature_with_mixed_tcs, run_cli, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("CLAUDE_NON_INTERACTIVE", "true")
        exit_code, data = run_cli(main, [str(feature_with_mixed_tcs)])
        assert exit_code == 0
        assert data["already_implemented"] == ["TC-E2E-002", "TC-UI-002"]
        assert data["next"] == "proceed"

    def test_cli_next_proceed_after_reimplement_ids(self, feature_with_mixed_tcs, run_cli, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("CLAUDE_NON_INTERACTIVE", raising=False)
        exit_code, data = run_cli(main, [str(feature_with_mixed_tcs), "--reimplement-ids", "TC-E2E-002"])
        assert exit_code == 0
        assert data["already_implemented"] == ["TC-UI-002"]
        assert data["next"] == "proceed"

    def test_cli_rejects_both_reimplement_flags(self, feature_with_mixed_tcs, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv",
            [
                "get_filtered_tcs.py",
                str(feature_with_mixed_tcs),
                "--include-implemented",
                "--reimplement-ids",
                "TC-E2E-002",
            ],
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "include_implemented" in err or "include-implemented" in err


class TestDecideReimplementNext:
    @pytest.mark.parametrize(
        "already,interactive,skip_prompt,expected",
        [
            ([], True, False, "proceed"),
            ([], False, False, "proceed"),
            (["TC-E2E-002"], True, False, "prompt_user"),
            (["TC-E2E-002"], False, False, "proceed"),
            (["TC-E2E-002"], True, True, "proceed"),
            (["TC-E2E-002"], False, True, "proceed"),
        ],
        ids=[
            "none-interactive",
            "none-non-interactive",
            "some-interactive",
            "some-non-interactive",
            "some-interactive-after-choice",
            "some-non-interactive-after-choice",
        ],
    )
    def test_prompt_user_only_when_implemented_exist_and_session_is_interactive(
        self, already, interactive, skip_prompt, expected
    ):
        assert decide_reimplement_next(already, interactive=interactive, skip_prompt=skip_prompt) == expected
