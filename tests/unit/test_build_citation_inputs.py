"""Unit tests for build_citation_inputs — deterministic construction of the citation gate's
inputs (ac_count/nfr_categories + validator results) from a resolved strategy file, or none.
"""

import json
import sys

import pytest

from scripts.build_citation_inputs import build_citation_inputs, main
from tests.helpers import objectives_citing_every_ac, write_testplan_with_objectives

STRATEGY_CONTENT = (
    "h3. Acceptance Criteria\n\n"
    "# Given a user registers a store, then it persists\n"
    "# Given a duplicate name, then it is rejected\n\n"
    "h3. Non-Functional Requirements\n\n"
    "* *Upgrade*: GET endpoints keep their shape\n"
)


class TestBuildCitationInputs:
    def test_ok_path_computes_ac_count_and_validator_results(self, tmp_path):
        write_testplan_with_objectives(tmp_path / "TestPlan.md", objectives_citing_every_ac(2, ["Upgrade"]))
        strategy_file = tmp_path / "strategy.md"
        strategy_file.write_text(STRATEGY_CONTENT)

        result = build_citation_inputs(str(tmp_path), str(strategy_file))

        assert result["status"] == "ok"
        assert result["ac_citations_result"]["valid"] is True
        assert result["ac_coverage_result"]["valid"] is True
        assert result["ac_coverage_result"]["ac_count"] == 2
        assert result["interface_coverage_result"]["valid"] is True

    def test_degraded_mode_without_strategy_skips_ac_coverage(self, tmp_path):
        write_testplan_with_objectives(tmp_path / "TestPlan.md", "1. Verify something (AC: #1 — cited)\n")

        result = build_citation_inputs(str(tmp_path), None)

        assert result["status"] == "degraded"
        assert result["ac_coverage_result"] is None
        assert result["ac_citations_result"]["valid"] is True  # presence-only fallback

    def test_missing_testplan_is_an_ordinary_invalid_result_not_an_execution_failure(self, tmp_path):
        result = build_citation_inputs(str(tmp_path), None)  # no TestPlan.md written

        assert result["status"] == "degraded"
        assert result["ac_citations_result"]["valid"] is False
        assert "error" in result["ac_citations_result"]

    def test_unreadable_strategy_file_raises_instead_of_downgrading_to_degraded_mode(self, tmp_path):
        write_testplan_with_objectives(tmp_path / "TestPlan.md", "1. Verify something (AC: #1 — cited)\n")

        # A directory can't be read as strategy text — stands in for parse_strat.py crashing on
        # corrupt/unreadable input. Must raise so the caller stops, not silently go "degraded".
        with pytest.raises(IsADirectoryError):
            build_citation_inputs(str(tmp_path), str(tmp_path))


class TestBuildCitationInputsCLI:
    def test_ok_path_prints_status_ok_and_exits_zero(self, tmp_path, capsys):
        write_testplan_with_objectives(tmp_path / "TestPlan.md", objectives_citing_every_ac(2, ["Upgrade"]))
        strategy_file = tmp_path / "strategy.md"
        strategy_file.write_text(STRATEGY_CONTENT)

        old_argv = sys.argv
        try:
            sys.argv = ["build_citation_inputs.py", str(tmp_path), "--strategy-file", str(strategy_file)]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit")
        finally:
            sys.argv = old_argv

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "ok"
        assert output["ac_citations_result"]["valid"] is True
        assert output["ac_coverage_result"]["valid"] is True
        assert output["ac_coverage_result"]["ac_count"] == 2
        assert output["interface_coverage_result"]["valid"] is True

    def test_execution_failure_exits_one_with_error_status(self, tmp_path, capsys):
        write_testplan_with_objectives(tmp_path / "TestPlan.md", "1. Verify something (AC: #1 — cited)\n")

        old_argv = sys.argv
        try:
            sys.argv = ["build_citation_inputs.py", str(tmp_path), "--strategy-file", str(tmp_path)]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("main() must exit with code 1")
        finally:
            sys.argv = old_argv

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "error"
        assert isinstance(output["error"], str) and output["error"]
