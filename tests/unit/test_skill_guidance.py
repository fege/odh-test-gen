"""Content regression tests for the test-gen skill guidance.

Guards the live-review lessons baked into the skills for issue #56
(opendatahub-tests#2187): the generation guardrails, the scoring-rubric checks,
the extended calibration example, and the live-validation prompt. These assert on
the shipped SKILL.md / rubric / calibration assets so the guidance cannot silently
regress. Mirrors tests/unit/test_template_structure.py.
"""

from tests.consts.skill_guidance_constants import (
    CALIBRATION_POOR_KEYWORDS,
    CALIBRATION_POOR_PYTEST,
    CALIBRATION_README,
    CASE_IMPLEMENT_KEYWORDS,
    CASE_IMPLEMENT_SKILL,
    GENERATE_GUIDANCE_KEYWORDS,
    GENERATE_SKILL,
    RUBRIC_SYNC_KEYWORDS,
    SCORE_RUBRIC,
    SCORE_RUBRIC_KEYWORDS,
)


class TestGenerationGuardrails:
    """generate-test-file SKILL.md must carry the false-green / activation-gate guidance."""

    def test_generate_skill_has_correctness_guardrails(self):
        text = GENERATE_SKILL.read_text()
        for keyword in GENERATE_GUIDANCE_KEYWORDS:
            assert keyword in text, f"generate-test-file SKILL.md missing guidance keyword: {keyword!r}"

    def test_generate_skill_classifies_skip_and_fail(self):
        text = GENERATE_SKILL.read_text()
        assert "pytest.skip" in text
        assert "pytest.fail" in text


class TestScoringRubricChecks:
    """The scorer rubric must encode the new correctness/safety checks (always in scope)."""

    def test_score_rubric_has_new_checks(self):
        text = SCORE_RUBRIC.read_text()
        for keyword in SCORE_RUBRIC_KEYWORDS:
            assert keyword in text, f"score-test-function.md missing rubric keyword: {keyword!r}"


class TestRubricStaysInSync:
    """The rubric is duplicated in the prompt and calibration README — keep them in sync."""

    def test_shared_keywords_in_both_copies(self):
        rubric_text = SCORE_RUBRIC.read_text()
        readme_text = CALIBRATION_README.read_text()
        for keyword in RUBRIC_SYNC_KEYWORDS:
            assert keyword in rubric_text, f"score-test-function.md missing shared keyword: {keyword!r}"
            assert keyword in readme_text, f"calibration/README.md missing shared keyword: {keyword!r}"


class TestPoorCalibrationExample:
    """The poor calibration example must demonstrate the new anti-patterns."""

    def test_poor_pytest_demonstrates_new_antipatterns(self):
        text = CALIBRATION_POOR_PYTEST.read_text()
        for keyword in CALIBRATION_POOR_KEYWORDS:
            assert keyword in text, f"poor-pytest-test.py missing anti-pattern marker: {keyword!r}"


class TestLiveValidationPrompt:
    """case-implement must prompt for live validation and report unverified coverage."""

    def test_case_implement_has_live_validation_and_unverified_coverage(self):
        text = CASE_IMPLEMENT_SKILL.read_text()
        for keyword in CASE_IMPLEMENT_KEYWORDS:
            assert keyword in text, f"case-implement SKILL.md missing keyword: {keyword!r}"
