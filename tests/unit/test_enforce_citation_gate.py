"""Unit tests for enforce_citation_gate — deterministic override of a wrongly-scored
Scope Fidelity when the review agent disagrees with the already-computed citation checks.
"""

from pathlib import Path

from scripts.enforce_citation_gate import enforce_citation_gate
from scripts.utils.frontmatter_utils import read_frontmatter, write_frontmatter

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
    data = {
        "feature": "Test",
        "source_key": "RHAISTRAT-1",
        "score": score if score is not None else sum(scores.values()),
        "pass": passed,
        "verdict": verdict,
        "scores": scores,
        "auto_revised": False,
        "last_updated": "2026-08-06",
    }
    if before_score is not None:
        data["before_score"] = before_score
        data["before_scores"] = before_scores or dict(scores)
    Path(path).write_text(
        body or "## Rubric Scores\n\n## Section-by-Section Feedback\n\nAll criteria passed — no improvements needed.\n"
    )
    write_frontmatter(str(path), data, "test-plan-review")
    return str(path)


class TestEnforceCitationGate:
    def test_valid_citations_no_override(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10)

        result = enforce_citation_gate(str(tmp_path), VALID_CITATIONS, VALID_COVERAGE)

        assert result == {"overridden": False}
        data, _ = read_frontmatter(review)
        assert data["scores"]["scope_fidelity"] == 2
        assert data["score"] == 10

    def test_degraded_mode_no_coverage_result_does_not_force_override(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=10)

        result = enforce_citation_gate(str(tmp_path), VALID_CITATIONS, None)

        assert result == {"overridden": False}

    def test_invalid_citations_caps_scope_fidelity_and_recomputes_score(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10, verdict="Ready", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, None)

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

    def test_override_can_flip_verdict_from_ready_to_revise(self, tmp_path):
        # specificity=2, grounding=2, scope_fidelity=2, actionability=1, consistency=1 -> total 8 (Ready)
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 1, "consistency": 1}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=8, verdict="Ready", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, None)

        assert result["scores"]["scope_fidelity"] == 1
        assert result["score"] == 7
        assert result["verdict"] == "Revise"
        assert result["pass"] is True

    def test_override_can_flip_verdict_to_rework_below_seven(self, tmp_path):
        # specificity=1, grounding=1, scope_fidelity=2, actionability=2, consistency=1 -> total 7 (Revise)
        scores = {"specificity": 1, "grounding": 1, "scope_fidelity": 2, "actionability": 2, "consistency": 1}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=7, verdict="Revise", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, None)

        assert result["scores"]["scope_fidelity"] == 1
        assert result["score"] == 6
        assert result["verdict"] == "Rework"
        assert result["pass"] is False

    def test_already_capped_scope_fidelity_is_left_alone(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 1, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=9, verdict="Ready", passed=True)

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, None)

        assert result == {"overridden": False}
        data, _ = read_frontmatter(review)
        assert data["score"] == 9  # untouched

    def test_missing_review_file_returns_none(self, tmp_path):
        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, None)

        assert result is None

    def test_first_pass_before_score_mirroring_current_score_is_corrected_too(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(
            tmp_path / "TestPlanReview.md", scores, score=10, before_score=10, before_scores=dict(scores)
        )

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, None)

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

        enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, None)

        data, _ = read_frontmatter(review)
        assert data["before_score"] == 7
        assert data["before_scores"]["scope_fidelity"] == 2  # untouched

    def test_missing_feedback_heading_still_overrides_frontmatter(self, tmp_path):
        # If the review agent's body doesn't match the expected shape, the score correction
        # (the part that actually drives filter_for_revision) must still apply.
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        review = _write_review(tmp_path / "TestPlanReview.md", scores, score=10, body="## Rubric Scores\n")

        result = enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, None)

        assert result["overridden"] is True
        data, _ = read_frontmatter(review)
        assert data["scores"]["scope_fidelity"] == 1
