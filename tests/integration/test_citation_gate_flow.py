"""Integration test: enforce_citation_gate -> filter_for_revision.

Reproduces the actual bug found on the vector_store_registration artifact: the review agent
reported Scope Fidelity 2/2 despite scripts.validate.validate_ac_citations saying the citations
are invalid. filter_for_revision decides purely from the persisted scores.* frontmatter — so
proving the fix means proving the corrected score actually flips that decision, not just that
enforce_citation_gate computes the right numbers in isolation.
"""

from scripts.enforce_citation_gate import enforce_citation_gate
from scripts.filter_for_revision import filter_for_revision
from scripts.utils.frontmatter_utils import write_frontmatter_with_body
from tests.helpers import build_review_payload

VALID_CITATIONS = {"valid": True, "total": 5, "cited": 5, "uncited": [], "invalid_citations": []}
VALID_COVERAGE = {"valid": True, "ac_count": 5, "covered": [1, 2, 3, 4, 5], "missing": []}
INVALID_CITATIONS = {
    "valid": False,
    "total": 5,
    "cited": 0,
    "uncited": [{"text": "1. Verify login (AC: Given a user logs in...)", "line_number": 79}],
    "invalid_citations": [],
}


def _write_review(path, scores, score=None, verdict="Ready", passed=True, before_score=None):
    data = build_review_payload(scores, score=score, verdict=verdict, passed=passed, before_score=before_score)
    body = "## Rubric Scores\n\n## Section-by-Section Feedback\n\nAll criteria passed.\n"
    return write_frontmatter_with_body(str(path), body, data, "test-plan-review")


class TestCitationGateToRevisionFlow:
    def test_wrongly_perfect_score_is_corrected_into_a_revision(self, tmp_path):
        # The exact shape of the real bug: review agent said everything is 2/2 despite
        # validate_ac_citations reporting invalid citations for this same TestPlan.md.
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=10, verdict="Ready", passed=True)

        assert filter_for_revision(str(tmp_path)) == "SKIP"  # the bug: never revises

        enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert filter_for_revision(str(tmp_path)) == "REVISE"  # fixed: now it does

    def test_first_pass_review_with_mirrored_before_score_still_revises(self, tmp_path):
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=10, before_score=10)

        enforce_citation_gate(str(tmp_path), INVALID_CITATIONS, VALID_COVERAGE)

        assert filter_for_revision(str(tmp_path)) == "REVISE"

    def test_genuinely_perfect_score_with_valid_citations_still_skips(self, tmp_path):
        # Guard against the gate over-triggering on a healthy plan.
        scores = {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2}
        _write_review(tmp_path / "TestPlanReview.md", scores, score=10, verdict="Ready", passed=True)

        enforce_citation_gate(str(tmp_path), VALID_CITATIONS, VALID_COVERAGE)

        assert filter_for_revision(str(tmp_path)) == "SKIP"
