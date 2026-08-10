"""Unit tests for scripts/cap_scope_fidelity.py — the stateless CLI wrapper around
enforce_citation_gate.cap_scope_fidelity(), for callers with no TestPlanReview.md to persist to
(test-plan-score, which presents a rubric assessment directly without writing a review file).
"""

import json
import sys

from scripts.cap_scope_fidelity import main

VALID_CITATIONS = {"valid": True, "total": 5, "cited": 5, "uncited": [], "invalid_citations": []}
VALID_COVERAGE = {"valid": True, "ac_count": 5, "covered": [1, 2, 3, 4, 5], "missing": []}
INVALID_CITATIONS = {"valid": False, "total": 5, "cited": 0, "uncited": [], "invalid_citations": []}


def _run(argv, capsys):
    old_argv = sys.argv
    try:
        sys.argv = ["cap_scope_fidelity.py", *argv]
        try:
            main()
        except SystemExit as exc:
            assert exc.code == 0
        else:
            raise AssertionError("main() must exit with code 0")
    finally:
        sys.argv = old_argv
    return json.loads(capsys.readouterr().out)


class TestCapScopeFidelityCLI:
    def test_ok_status_when_no_override_needed(self, capsys):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}

        output = _run(
            [
                "--scores",
                json.dumps(scores),
                "--ac-citations-result",
                json.dumps(VALID_CITATIONS),
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ],
            capsys,
        )

        assert output == {"status": "ok", "scores": scores}

    def test_overridden_status_when_citations_invalid(self, capsys):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}

        output = _run(
            [
                "--scores",
                json.dumps(scores),
                "--ac-citations-result",
                json.dumps(INVALID_CITATIONS),
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ],
            capsys,
        )

        assert output["status"] == "overridden"
        assert output["scores"]["scope_fidelity"] == 1
        assert output["score"] == 9
        assert output["verdict"] == "Ready"
        assert output["pass"] is True

    def test_malformed_scores_json_exits_zero_with_error_status(self, capsys):
        output = _run(
            [
                "--scores",
                "NOT-VALID-JSON{{{",
                "--ac-citations-result",
                json.dumps(VALID_CITATIONS),
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ],
            capsys,
        )

        assert output["status"] == "error"

    def test_missing_valid_field_exits_zero_with_error_status(self, capsys):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}

        output = _run(
            [
                "--scores",
                json.dumps(scores),
                "--ac-citations-result",
                json.dumps({"total": 5}),
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ],
            capsys,
        )

        assert output["status"] == "error"
        assert "valid" in output["error"]
