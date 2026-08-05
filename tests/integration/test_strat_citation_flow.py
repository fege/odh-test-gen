"""Integration test: STRAT parsing -> gate_inputs -> generated TestPlan.md citation validation.

parse_acceptance_criteria (STRAT side) assigns AC numbers, and gate_inputs derives ac_count/
nfr_categories from them; validate_ac_citations/validate_ac_coverage (TestPlan.md side) check
citations against those same values.
Chain a real STRAT's gate_inputs output into the validators that consume it.
"""

from scripts.utils.strat_utils import gate_inputs
from scripts.validate import validate_ac_citations, validate_ac_coverage
from tests.helpers import objectives_citing_every_ac, write_testplan_with_objectives

STRAT_CONTENT = (
    "h3. Acceptance Criteria\n\n"
    "* Given a user registers a store, when submitted, then it persists\n"
    "* Given a duplicate name, when submitted, then it is rejected\n\n"
    "h3. Testability: Additional Acceptance Criteria\n\n"
    "# *Malformed secret*: Given a secret exists but is missing a required key, "
    "when submitted, then a clear error is returned\n\n"
    "h3. Non-Functional Requirements\n\n"
    "* *Security*: Namespace-scoped RBAC enforced on every write\n"
)


class TestStratToCitationFlow:
    def test_strat_derived_ac_count_matches_generated_citations(self, tmp_path):
        inputs = gate_inputs(STRAT_CONTENT)
        assert inputs["ac_count"] == 3  # 2 main ACs + 1 folded-in Testability edge case
        assert inputs["nfr_categories"] == ["Security"]
        nfr_categories = inputs["nfr_categories"]

        body = objectives_citing_every_ac(inputs["ac_count"], nfr_categories)
        testplan = write_testplan_with_objectives(tmp_path / "TestPlan.md", body)

        citations = validate_ac_citations(testplan, ac_count=inputs["ac_count"], nfr_categories=nfr_categories)
        coverage = validate_ac_coverage(testplan, ac_count=inputs["ac_count"])

        assert citations["valid"] is True
        assert citations["invalid_citations"] == []
        assert coverage["valid"] is True
        assert coverage["missing"] == []

    def test_citation_beyond_strat_derived_ac_count_fails(self, tmp_path):
        # Simulates an analyzer fabricating a 4th AC that doesn't exist in the STRAT.
        inputs = gate_inputs(STRAT_CONTENT)
        nfr_categories = inputs["nfr_categories"]
        body = (
            "1. Verify AC 1 (AC: #1 — placeholder)\n"
            "2. Verify AC 2 (AC: #2 — placeholder)\n"
            "3. Verify AC 3 (AC: #3 — placeholder)\n"
            "4. Verify a fabricated AC (AC: #4 — placeholder)\n"
        )
        testplan = write_testplan_with_objectives(tmp_path / "TestPlan.md", body)

        citations = validate_ac_citations(testplan, ac_count=inputs["ac_count"], nfr_categories=nfr_categories)

        assert citations["valid"] is False
        assert citations["invalid_citations"][0]["reasons"] == ["out_of_range"]

    def test_ac_missing_from_generated_plan_fails_coverage(self, tmp_path):
        # Simulates an analyzer dropping AC #2 entirely (no objective cites it at all) — the
        # exact failure mode ac-coverage exists to catch, using a real STRAT-derived ac_count.
        inputs = gate_inputs(STRAT_CONTENT)
        body = "1. Verify AC 1 (AC: #1 — placeholder)\n2. Verify AC 3 (AC: #3 — placeholder)\n"
        testplan = write_testplan_with_objectives(tmp_path / "TestPlan.md", body)

        coverage = validate_ac_coverage(testplan, ac_count=inputs["ac_count"])

        assert coverage["valid"] is False
        assert coverage["missing"] == [2]
