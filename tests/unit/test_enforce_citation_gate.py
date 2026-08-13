"""Unit tests for enforce_citation_gate — deterministic override of a wrongly-scored
Scope Fidelity when the review agent disagrees with the already-computed citation checks.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.enforce_citation_gate import cap_scope_fidelity, enforce_citation_gate, main
from scripts.utils.frontmatter_utils import read_frontmatter, write_frontmatter_with_body
from tests.helpers import build_review_payload

VALID_CITATIONS = {"valid": True, "total": 5, "cited": 5, "uncited": [], "invalid_citations": []}
VALID_COVERAGE = {"valid": True, "ac_count": 5, "covered": [1, 2, 3, 4, 5], "missing": []}

INVALID_CITATIONS = {
    "valid": False,
    "total": 2,
    "cited": 0,
    "uncited": [{"text": "1. Verify login (AC: Given a user logs in...)", "line_number": 79}],
    "invalid_citations": [
        {"text": "2. Verify logout (AC: #9 — out of range)", "line_number": 82, "reasons": ["out_of_range"]}
    ],
}
INVALID_COVERAGE = {"valid": False, "ac_count": 5, "covered": [1], "missing": [2, 3, 4, 5]}


def _write_review(
    path, scores, score=None, verdict="Ready", passed=True, body=None, before_score=None, before_scores=None
):
    data = build_review_payload(
        scores, score=score, verdict=verdict, passed=passed, before_score=before_score, before_scores=before_scores
    )
    return write_frontmatter_with_body(
        path,
        body or "## Rubric Scores\n\n## Section-by-Section Feedback\n\nAll criteria passed — no improvements needed.\n",
        data,
        "test-plan-review",
    )


class TestCapScopeFidelity:
    """Pure-function tests for cap_scope_fidelity — no file I/O, shared by enforce_citation_gate
    (which persists the result to TestPlanReview.md) and test-plan-score (which has no review
    file and only needs the corrected numbers to present to the user).
    """

    def test_no_override_when_citations_and_coverage_valid(self):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}

        result = cap_scope_fidelity(scores, VALID_CITATIONS, VALID_COVERAGE)

        assert result == {"overridden": False, "scores": scores}

    def test_override_when_citations_invalid(self):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}

        result = cap_scope_fidelity(scores, INVALID_CITATIONS, VALID_COVERAGE)

        assert result["overridden"] is True
        assert result["scores"]["scope_fidelity"] == 1
        assert result["score"] == 9
        assert result["verdict"] == "Ready"
        assert result["pass"] is True

    def test_override_when_coverage_invalid(self):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}

        result = cap_scope_fidelity(scores, VALID_CITATIONS, INVALID_COVERAGE)

        assert result["overridden"] is True
        assert result["scores"]["scope_fidelity"] == 1

    def test_already_capped_scope_fidelity_is_left_alone(self):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 1, "actionability": 2, "consistency": 2}

        result = cap_scope_fidelity(scores, INVALID_CITATIONS, VALID_COVERAGE)

        assert result == {"overridden": False, "scores": scores}

    def test_does_not_mutate_the_input_scores_dict(self):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        original = dict(scores)

        cap_scope_fidelity(scores, INVALID_CITATIONS, VALID_COVERAGE)

        assert scores == original

    @pytest.mark.parametrize(
        "citations_result,coverage_result",
        [
            pytest.param({"total": 5}, VALID_COVERAGE, id="missing_valid_in_citations"),
            pytest.param(VALID_CITATIONS, {"missing": []}, id="missing_valid_in_coverage"),
            pytest.param({**VALID_CITATIONS, "valid": "false"}, VALID_COVERAGE, id="string_false_in_citations"),
            pytest.param(VALID_CITATIONS, {**VALID_COVERAGE, "valid": "false"}, id="string_false_in_coverage"),
            pytest.param({"valid": False, "uncited": [None]}, VALID_COVERAGE, id="null_entry_in_uncited"),
            pytest.param(
                {"valid": False, "invalid_citations": [None]}, VALID_COVERAGE, id="null_entry_in_invalid_citations"
            ),
            pytest.param({"valid": False, "uncited": "not-a-list"}, VALID_COVERAGE, id="uncited_not_a_list"),
            pytest.param(
                {"valid": False, "invalid_citations": [{"text": "x", "line_number": 1}]},
                VALID_COVERAGE,
                id="invalid_citation_missing_reasons",
            ),
            pytest.param(
                {"valid": False, "invalid_citations": [{"text": "x", "line_number": 1, "reasons": [None]}]},
                VALID_COVERAGE,
                id="null_reasons_element_in_invalid_citations",
            ),
        ],
    )
    def test_malformed_result_raises(self, citations_result, coverage_result):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}

        with pytest.raises(ValueError):
            cap_scope_fidelity(scores, citations_result, coverage_result)

    @pytest.mark.parametrize(
        "invalid_scores",
        [
            pytest.param({"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2}, id="missing_key"),
            pytest.param(
                {
                    "specificity": 2,
                    "grounding": 2,
                    "scope_fidelity": 2,
                    "actionability": 2,
                    "consistency": 2,
                    "extra": 1,
                },
                id="extra_key",
            ),
            pytest.param(
                {"specificity": 2, "grounding": True, "scope_fidelity": 2, "actionability": 2, "consistency": 2},
                id="bool_value",
            ),
            pytest.param(
                {"specificity": 2, "grounding": "2", "scope_fidelity": 2, "actionability": 2, "consistency": 2},
                id="str_value",
            ),
            pytest.param(
                {"specificity": 3, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2},
                id="out_of_range_high",
            ),
            pytest.param(
                {"specificity": -1, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2},
                id="out_of_range_low",
            ),
        ],
    )
    def test_invalid_scores_raises(self, invalid_scores):
        with pytest.raises(ValueError):
            cap_scope_fidelity(invalid_scores, VALID_CITATIONS, VALID_COVERAGE)


class TestEnforceCitationGate:
    def test_valid_citations_no_override(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10)

        result = enforce_citation_gate(str(tmp_path), VALID_CITATIONS, VALID_COVERAGE)

        assert result == {"overridden": False}
        data, _ = read_frontmatter(review)
        assert data["scores"]["scope_fidelity"] == 2
        assert data["score"] == 10

    def test_invalid_citations_caps_scope_fidelity_and_recomputes_score(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10, verdict="Ready", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert result["overridden"] is True
        assert result["scores"]["scope_fidelity"] == 1
        assert result["score"] == 9
        assert result["verdict"] == "Ready"  # 9 >= 8 and no criterion is 0
        assert result["pass"] is True

        data, _ = read_frontmatter(review)
        assert data["scores"]["scope_fidelity"] == 1
        assert data["score"] == 9

    def test_override_injects_feedback_note_with_specifics(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10)

        enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, INVALID_COVERAGE)

        body = Path(review).read_text()
        assert "## Section-by-Section Feedback" in body
        assert "Line 79" in body  # uncited objective
        assert "Line 82" in body  # invalid citation
        assert "out_of_range" in body
        assert "[2, 3, 4, 5]" in body  # missing AC numbers from coverage

    def test_note_building_failure_leaves_no_partial_update(self, tmp_path):
        # The note is built from the same untrusted results already validated up front, but this
        # proves the *ordering* independent of what validation does or doesn't catch: if building
        # the note ever fails, the frontmatter must not have been written already.
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10)
        original_data, _ = read_frontmatter(review)
        original_body = Path(review).read_text()

        with patch("scripts.enforce_citation_gate._build_feedback_note", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        data, _ = read_frontmatter(review)
        assert data == original_data
        assert Path(review).read_text() == original_body

    def test_valid_citations_do_not_touch_body(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10)
        original_body = Path(review).read_text()

        enforce_citation_gate(str(tmp_path), VALID_CITATIONS, VALID_COVERAGE)

        assert Path(review).read_text() == original_body

    def test_invalid_ac_coverage_alone_also_triggers_override(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=10)

        result = enforce_citation_gate(str(tmp_path), VALID_CITATIONS, INVALID_COVERAGE)

        assert result["overridden"] is True
        assert result["scores"]["scope_fidelity"] == 1

    def test_override_recomputes_score_but_verdict_stays_revise(self, tmp_path):
        # specificity=2, grounding=2, scope_fidelity=2, actionability=1, consistency=1 -> tot 8, but
        # actionability=1 fails the Ready gate so the starting verdict is already Revise, not Ready.
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 1, "consistency": 1}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=8, verdict="Revise", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert result["scores"]["scope_fidelity"] == 1
        assert result["score"] == 7
        assert result["verdict"] == "Revise"
        assert result["pass"] is True

    def test_override_can_flip_verdict_from_ready_to_revise(self, tmp_path):
        # specificity=1, grounding=1, scope_fidelity=2, actionability=2, consistency=2 -> tot 8, no
        # zero, actionability=2 -> starting verdict is genuinely Ready. A defect that caps
        # scope_fidelity but never recalls compute_verdict_and_pass would leave verdict="Ready"
        # here, unlike test_override_recomputes_score_but_verdict_stays_revise above where the
        # persisted verdict coincidentally matches even without recomputation.
        scores = {"specificity": 1, "grounding": 1, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=8, verdict="Ready", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert result["scores"]["scope_fidelity"] == 1
        assert result["score"] == 7
        assert result["verdict"] == "Revise"
        assert result["pass"] is True

    def test_override_can_flip_verdict_to_rework_below_seven(self, tmp_path):
        # specificity=1, grounding=1, scope_fidelity=2, actionability=2, consistency=1 -> total 7 (Revise)
        scores = {"specificity": 1, "grounding": 1, "scope_fidelity": 2, "actionability": 2, "consistency": 1}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=7, verdict="Revise", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert result["scores"]["scope_fidelity"] == 1
        assert result["score"] == 6
        assert result["verdict"] == "Rework"
        assert result["pass"] is False

    def test_already_capped_scope_fidelity_is_left_alone(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 1, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=9, verdict="Ready", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert result == {"overridden": False}
        data, _ = read_frontmatter(review)
        assert data["score"] == 9  # untouched

    def test_missing_review_file_returns_none(self, tmp_path):
        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert result is None

    def test_first_pass_before_score_mirroring_current_score_is_corrected_too(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(
            tmp_path / "TestPlanReview.md", scores, score=10, before_score=10, before_scores=dict(scores)
        )

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert result["score"] == 9
        data, _ = read_frontmatter(review)
        assert data["before_score"] == 9
        assert data["before_scores"]["scope_fidelity"] == 1

    def test_genuine_prior_cycle_before_score_is_left_alone(self, tmp_path):
        # before_score differs from score -> it's a real baseline from an earlier revision
        # cycle, not a same-pass mirror. Must not be touched.
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(
            tmp_path / "TestPlanReview.md",
            scores,
            score=10,
            before_score=7,
            before_scores={"specificity": 1, "grounding": 1, "scope_fidelity": 2, "actionability": 2, "consistency": 1},
        )

        enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        data, _ = read_frontmatter(review)
        assert data["before_score"] == 7
        assert data["before_scores"]["scope_fidelity"] == 2  # untouched

    def test_missing_feedback_heading_still_overrides_frontmatter(self, tmp_path):
        # If the review agent's body doesn't match the expected shape, the score correction
        # (the part that actually drives filter_for_revision) must still apply.
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10, body="## Rubric Scores\n")

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert result["overridden"] is True
        data, _ = read_frontmatter(review)
        assert data["scores"]["scope_fidelity"] == 1


class TestEnforceCitationGateFailsClosedOnMalformedResults:
    """A malformed ac_citations_result/ac_coverage_result must reject outright — never silently
    default a missing/wrong-typed `valid` field to True. `"valid": "false"` is the sharpest case:
    it's a non-empty string, so Python truthiness alone would treat it as truthy/OK.
    """

    @pytest.mark.parametrize(
        "citations_result,coverage_result",
        [
            pytest.param({"total": 5}, VALID_COVERAGE, id="missing_valid_in_citations"),
            pytest.param(VALID_CITATIONS, {"missing": []}, id="missing_valid_in_coverage"),
            pytest.param({**VALID_CITATIONS, "valid": "false"}, VALID_COVERAGE, id="string_false_in_citations"),
            pytest.param(VALID_CITATIONS, {**VALID_COVERAGE, "valid": "false"}, id="string_false_in_coverage"),
            pytest.param("not-a-dict", VALID_COVERAGE, id="citations_not_a_dict"),
            pytest.param(VALID_CITATIONS, "not-a-dict", id="coverage_not_a_dict"),
            pytest.param({"valid": False, "uncited": [None]}, VALID_COVERAGE, id="null_entry_in_uncited"),
            pytest.param(
                {"valid": False, "invalid_citations": [None]}, VALID_COVERAGE, id="null_entry_in_invalid_citations"
            ),
            pytest.param({"valid": False, "uncited": "not-a-list"}, VALID_COVERAGE, id="uncited_not_a_list"),
            pytest.param(
                {"valid": False, "invalid_citations": [{"text": "x", "line_number": 1}]},
                VALID_COVERAGE,
                id="invalid_citation_missing_reasons",
            ),
            pytest.param(
                {"valid": False, "invalid_citations": [{"text": "x", "line_number": 1, "reasons": [None]}]},
                VALID_COVERAGE,
                id="null_reasons_element_in_invalid_citations",
            ),
        ],
    )
    def test_malformed_result_raises_and_does_not_touch_review(self, tmp_path, citations_result, coverage_result):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10)
        original_data, _ = read_frontmatter(review)

        with pytest.raises(ValueError):
            enforce_citation_gate(str(tmp_path), citations_result, coverage_result)

        data, _ = read_frontmatter(review)
        assert data == original_data  # rejected before touching the review


class TestEnforceCitationGateCLI:
    """CLI-level tests for main() — exercises JSON parsing and ValidationError handling."""

    def test_malformed_ac_citations_json_exits_zero_with_stderr_diagnostic(self, tmp_path, capsys):
        old_argv = sys.argv
        try:
            sys.argv = [
                "enforce_citation_gate.py",
                str(tmp_path),
                "--ac-citations-result",
                "NOT-VALID-JSON{{{",
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit with code 0")
        finally:
            sys.argv = old_argv

        captured = capsys.readouterr()
        assert "malformed --ac-citations-result JSON" in captured.err
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert "malformed --ac-citations-result JSON" in output["error"]

    def test_malformed_ac_coverage_json_exits_zero_with_stderr_diagnostic(self, tmp_path, capsys):
        old_argv = sys.argv
        try:
            sys.argv = [
                "enforce_citation_gate.py",
                str(tmp_path),
                "--ac-citations-result",
                json.dumps(VALID_CITATIONS),
                "--ac-coverage-result",
                "%%%bad%%%",
            ]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit with code 0")
        finally:
            sys.argv = old_argv

        captured = capsys.readouterr()
        assert "malformed --ac-coverage-result JSON" in captured.err
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert "malformed --ac-coverage-result JSON" in output["error"]

    @pytest.mark.parametrize(
        "citations_payload,coverage_payload,bad_flag",
        [
            pytest.param({"total": 5}, VALID_COVERAGE, "--ac-citations-result", id="citations_missing_valid"),
            pytest.param(
                VALID_CITATIONS,
                {**VALID_COVERAGE, "valid": "false"},
                "--ac-coverage-result",
                id="coverage_string_false",
            ),
        ],
    )
    def test_malformed_valid_field_exits_zero_with_stderr_diagnostic(
        self, tmp_path, capsys, citations_payload, coverage_payload, bad_flag
    ):
        old_argv = sys.argv
        try:
            sys.argv = [
                "enforce_citation_gate.py",
                str(tmp_path),
                "--ac-citations-result",
                json.dumps(citations_payload),
                "--ac-coverage-result",
                json.dumps(coverage_payload),
            ]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit with code 0")
        finally:
            sys.argv = old_argv

        captured = capsys.readouterr()
        assert bad_flag in captured.err
        assert "valid" in captured.err
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert bad_flag in output["error"]
        assert "valid" in output["error"]

    def test_invalid_review_frontmatter_exits_zero_with_stderr_diagnostic(self, tmp_path, capsys):
        # Write a TestPlanReview.md whose frontmatter violates the schema:
        # score=99 is out of range (max 10) and doesn't match sum of scores.
        review_path = tmp_path / "TestPlanReview.md"
        review_path.write_text(
            "---\n"
            "feature: Test\n"
            "source_key: RHAISTRAT-1\n"
            "score: 99\n"
            "pass: true\n"
            "verdict: Ready\n"
            "scores:\n"
            "  specificity: 2\n"
            "  grounding: 2\n"
            "  scope_fidelity: 2\n"
            "  actionability: 2\n"
            "  consistency: 2\n"
            "auto_revised: false\n"
            "last_updated: '2026-08-06'\n"
            "---\n"
            "## Rubric Scores\n"
        )
        old_argv = sys.argv
        try:
            sys.argv = [
                "enforce_citation_gate.py",
                str(tmp_path),
                "--ac-citations-result",
                json.dumps(INVALID_CITATIONS),
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit with code 0")
        finally:
            sys.argv = old_argv

        captured = capsys.readouterr()
        assert "invalid TestPlanReview.md" in captured.err
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert "invalid TestPlanReview.md" in output["error"]

    def test_happy_path_override_prints_overridden_status_to_stdout(self, tmp_path, capsys):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=10, verdict="Ready", passed=True)

        old_argv = sys.argv
        try:
            sys.argv = [
                "enforce_citation_gate.py",
                str(tmp_path),
                "--ac-citations-result",
                json.dumps(INVALID_CITATIONS),
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
        finally:
            sys.argv = old_argv

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "overridden"
        assert output["scores"]["scope_fidelity"] == 1
        assert output["score"] == 9
        assert output["verdict"] == "Ready"
        assert output["pass"] is True

    def test_no_override_needed_prints_ok_status_to_stdout(self, tmp_path, capsys):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=10, verdict="Ready", passed=True)

        old_argv = sys.argv
        try:
            sys.argv = [
                "enforce_citation_gate.py",
                str(tmp_path),
                "--ac-citations-result",
                json.dumps(VALID_CITATIONS),
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
        finally:
            sys.argv = old_argv

        assert json.loads(capsys.readouterr().out) == {"status": "ok"}

    def test_missing_review_file_prints_skip_status_to_stdout(self, tmp_path, capsys):
        old_argv = sys.argv
        try:
            sys.argv = [
                "enforce_citation_gate.py",
                str(tmp_path),
                "--ac-citations-result",
                json.dumps(VALID_CITATIONS),
                "--ac-coverage-result",
                json.dumps(VALID_COVERAGE),
            ]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
        finally:
            sys.argv = old_argv

        assert json.loads(capsys.readouterr().out) == {"status": "skip"}
