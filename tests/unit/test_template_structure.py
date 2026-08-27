"""
Structural regression tests for skill templates.

Ensures skills/test-plan-create/test-plan-template.md stays in sync with
the deterministic validators that check LLM-generated output against it.
"""

import re

import pytest

from scripts.utils.markdown_utils import extract_section, has_citation, parse_citations
from scripts.utils.schemas import TEMPLATE_HEADINGS, _parse_template_headings, _require_headings
from scripts.validate import validate_interface_types, validate_structure
from tests.constants import REPO_ROOT

TEMPLATE_PATH = REPO_ROOT / "skills" / "test-plan-create" / "test-plan-template.md"
CREATE_SKILL_PATH = REPO_ROOT / "skills" / "test-plan-create" / "SKILL.md"
ENDPOINT_ANALYZER_SKILL_PATH = REPO_ROOT / "skills" / "test-plan-analyze-endpoints" / "SKILL.md"
CREATE_CASES_SKILL_PATH = REPO_ROOT / "skills" / "test-plan-create-cases" / "SKILL.md"
REVIEW_SKILL_PATH = REPO_ROOT / "skills" / "test-plan-review" / "SKILL.md"
SCORE_SKILL_PATH = REPO_ROOT / "skills" / "test-plan-score" / "SKILL.md"
SCORE_PROMPT_PATH = REPO_ROOT / "skills" / "test-plan-review" / "prompts" / "score-agent.md"
REVISE_PROMPT_PATH = REPO_ROOT / "skills" / "test-plan-review" / "prompts" / "revise-agent.md"
HUMAN_REVIEW_GUIDE_PATH = REPO_ROOT / "docs" / "human-review-guide.md"

E2E_OR_UI_DIAGNOSTIC_KEY = "missing_e2e_or_ui_in_6_2"

_E2E_COVERAGE_CONTRACT_PATHS = (
    REVIEW_SKILL_PATH,
    SCORE_SKILL_PATH,
    SCORE_PROMPT_PATH,
    REVISE_PROMPT_PATH,
    CREATE_CASES_SKILL_PATH,
    HUMAN_REVIEW_GUIDE_PATH,
)

_SECTION_1_3_HEADING = "### 1.3 Test Objectives"
_SCOPE_BEARING_SECTIONS = ("1.2", "2.3", "7.1", "7.2", "7.3", "7.4", "7.5", "8")


def _normalise_whitespace(text):
    return re.sub(r"\s+", " ", text).strip()


def _has_e2e_or_ui_requirement(text):
    normalized = _normalise_whitespace(text)
    return bool(
        re.search(
            r"at least one.{0,220}TC-E2E-\*.{0,220}\bor\b.{0,220}TC-UI-\*",
            normalized,
            re.IGNORECASE,
        )
        or re.search(
            r"at least one.{0,220}TC-UI-\*.{0,220}\bor\b.{0,220}TC-E2E-\*",
            normalized,
            re.IGNORECASE,
        )
    )


def _has_ac_less_scope_gaps_instruction(text):
    paragraphs = [_normalise_whitespace(paragraph) for paragraph in text.split("\n\n")]

    return any(
        "## Gaps" in paragraph
        and re.search(r"\b(?:every|each|all)\b.{0,100}\bin[- ]scope\b", paragraph, re.IGNORECASE)
        and re.search(
            r"(?:excluded|omitted|left out).{0,140}Section 1\.3|Section 1\.3.{0,140}(?:excluded|omitted|left out)",
            paragraph,
            re.IGNORECASE,
        )
        and re.search(
            r"(?:lack|without|no|does not have|not have).{0,80}backing (?:AC|Acceptance Criterion)",
            paragraph,
            re.IGNORECASE,
        )
        and re.search(r"(?:record|log|disclos|include).{0,120}Gaps", paragraph, re.IGNORECASE)
        for paragraph in paragraphs
    )


class TestTemplateSection4Structure:
    """Section 4 (Interfaces Under Test) in the template must match the deterministic validator."""

    def test_template_section4_has_no_priority_column(self):
        result = validate_interface_types(str(TEMPLATE_PATH))

        assert result["header"] == ["Interface", "Type", "Purpose"]
        assert "{REST/gRPC/UI/CLI/CRD}" in TEMPLATE_PATH.read_text()

    def test_template_has_no_bold_pseudo_headings(self):
        result = validate_structure(str(TEMPLATE_PATH))

        assert result["valid"] is True, f"Template structure invalid: {result}"
        assert result["pseudo_headings"] == [], f"Template contains bold pseudo-headings: {result['pseudo_headings']}"

    def test_filled_in_template_has_no_bold_pseudo_headings(self, tmp_path):
        """A raw placeholder like `{team_name}` starts with `{`, not `[A-Z]`, so it can dodge the
        pseudo-heading regex while a real filled-in value (e.g. "AI Hub QE Team") matches it —
        check a realistic instance, not just the untouched template."""
        filled = TEMPLATE_PATH.read_text()
        for placeholder, value in {
            "{feature_name}": "Vector Store Registration",
            "{team_name}": "AI Hub QE Team",
            "{testing_focus}": "Registration and Lifecycle Testing",
            "{source_key}": "RHAISTRAT-1746",
            "{strat_url}": "https://issues.redhat.com/browse/RHAISTRAT-1746",
            "{today_date}": "2026-08-27",
        }.items():
            filled = filled.replace(placeholder, value)

        plan = tmp_path / "TestPlan.md"
        plan.write_text(filled)

        result = validate_structure(str(plan))

        assert result["pseudo_headings"] == [], (
            f"Filled-in template has bold pseudo-headings: {result['pseudo_headings']}"
        )


class TestTemplateHeadingsFailClosed:
    """The bundled template must expose every heading number the validators index directly."""

    def test_missing_heading_raises(self):
        with pytest.raises(ValueError, match="missing required section headings"):
            _require_headings({"1": "## 1. Overview"})

    def test_missing_template_file_raises_clear_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr("scripts.utils.schemas._TEMPLATE_PATH", tmp_path / "nonexistent-template.md")
        with pytest.raises(ValueError, match="template"):
            _parse_template_headings()


class TestTemplateCitationFormat:
    """Section 1.3 in the template must document a citation format the validator actually accepts."""

    def _section_1_3_text(self):
        content = TEMPLATE_PATH.read_text()
        lines, _ = extract_section(content, _SECTION_1_3_HEADING)
        return "\n".join(lines)

    def test_section_1_3_has_no_legacy_bracket_citation(self):
        assert "(AC: [" not in self._section_1_3_text()

    def test_section_1_3_example_is_accepted_by_validator(self):
        assert has_citation(self._section_1_3_text()) is True

    def test_section_1_3_example_parses_to_well_formed_citation(self):
        cites = parse_citations(self._section_1_3_text())

        assert cites, "template Section 1.3 must contain a parseable (AC: #N — text) or (NFR: category — text) example"
        assert cites[0]["kind"] in {"AC", "NFR"}


class TestGeneratedPlanEvidenceContracts:
    @pytest.mark.parametrize("section", _SCOPE_BEARING_SECTIONS)
    def test_scope_bearing_template_sections_require_an_objective_marker(self, section):
        lines, _ = extract_section(TEMPLATE_PATH.read_text(), TEMPLATE_HEADINGS[section])

        assert re.search(r"\(Objective:\s*#N\)", "\n".join(lines))

    def test_creation_instructions_validate_scope_coverage_before_review(self):
        instructions = CREATE_SKILL_PATH.read_text()

        assert "(Objective: #N)" in instructions
        assert "scripts/build_citation_inputs.py" in instructions
        assert ".scope_coverage_result.valid" in instructions

    def test_scope_fidelity_revision_guidance_can_repair_every_scope_bearing_section(self):
        scope_fidelity_row = next(
            line for line in REVISE_PROMPT_PATH.read_text().splitlines() if line.startswith("| **Scope Fidelity**")
        )

        assert "(Objective: #N)" in scope_fidelity_row
        for section in _SCOPE_BEARING_SECTIONS:
            assert section in scope_fidelity_row

    def test_tbd_guidance_matches_the_validator_resolution_path_contract(self):
        template = TEMPLATE_PATH.read_text()
        creation_instructions = CREATE_SKILL_PATH.read_text()
        score_prompt = SCORE_PROMPT_PATH.read_text()
        revision_instructions = REVISE_PROMPT_PATH.read_text()

        assert "TBD — Resolution:" in template
        assert "explicit resolution path" in creation_instructions
        assert 'plain "TBD"' not in creation_instructions
        assert "explicit resolution path" in score_prompt
        assert "explicit resolution path" in revision_instructions
        assert "TBD — Resolution:" in revision_instructions
        assert "TBD — pending" not in revision_instructions

    def test_scope_fidelity_enforcement_documents_every_capped_evidence_input(self):
        score_prompt = SCORE_PROMPT_PATH.read_text()
        scope_fidelity_section = score_prompt.split("### 3. SCOPE FIDELITY", maxsplit=1)[1].split(
            "### 4. ACTIONABILITY", maxsplit=1
        )[0]
        enforcement = scope_fidelity_section.split("**Enforcement", maxsplit=1)[1]

        for result_name in (
            "AC_CITATIONS_RESULT",
            "AC_COVERAGE_RESULT",
            "SCOPE_CHECK_RESULT",
            "SCOPE_COVERAGE_RESULT",
        ):
            assert f"`{result_name}.valid == false`" in enforcement

    @pytest.mark.parametrize("instructions_path", _E2E_COVERAGE_CONTRACT_PATHS)
    def test_e2e_or_ui_coverage_instructions_consume_renamed_diagnostic(self, instructions_path):
        instructions = instructions_path.read_text()

        assert E2E_OR_UI_DIAGNOSTIC_KEY in instructions
        assert _has_e2e_or_ui_requirement(instructions)

    def test_template_section_6_note_requires_e2e_or_ui_reference(self):
        section_lines, _ = extract_section(TEMPLATE_PATH.read_text(), TEMPLATE_HEADINGS["6"])
        section = "\n".join(section_lines)

        assert _has_e2e_or_ui_requirement(section)
        assert "At least one E2E scenario MUST" not in section

    def test_human_review_guide_requires_e2e_or_ui_reference_for_populated_rows(self):
        guide = HUMAN_REVIEW_GUIDE_PATH.read_text()
        normalized_guide = _normalise_whitespace(guide)

        assert _has_e2e_or_ui_requirement(guide)
        assert E2E_OR_UI_DIAGNOSTIC_KEY in guide
        assert re.search(
            r"`missing_in_6_2`.{0,240}\bno\b.{0,40}\bfilled\b.{0,40}\brow\b",
            normalized_guide,
            re.IGNORECASE,
        )
        assert re.search(
            r"`missing_e2e_or_ui_in_6_2`.{0,320}"
            r"\bdeclared interface\b.{0,120}\brow\b.{0,120}"
            r"(?:without either|neither|without both|lacks both)",
            normalized_guide,
            re.IGNORECASE,
        )
        assert re.search(
            r"`missing_e2e_or_ui_in_6_2`.{0,500}\bdeficient duplicate(?:s)?\b",
            normalized_guide,
            re.IGNORECASE,
        )

    def test_creation_instructions_disclose_ac_less_in_scope_exclusions_in_gaps(self):
        paragraphs = [_normalise_whitespace(paragraph) for paragraph in CREATE_SKILL_PATH.read_text().split("\n\n")]

        assert any(
            "TestPlanGaps.md" in paragraph
            and "Section 1.2" in paragraph
            and "Section 1.3" in paragraph
            and re.search(r"in[- ]scope", paragraph, re.IGNORECASE)
            and re.search(r"exclud|omit", paragraph, re.IGNORECASE)
            and re.search(
                r"(?:lack|without|no|does not have|not have).{0,80}backing (?:AC|Acceptance Criterion)",
                paragraph,
                re.IGNORECASE,
            )
            and re.search(r"backing (?:AC|Acceptance Criterion)", paragraph, re.IGNORECASE)
            and re.search(r"record|log|disclos", paragraph, re.IGNORECASE)
            for paragraph in paragraphs
        )

    def test_endpoint_analyzer_discloses_ac_less_in_scope_exclusions_in_its_gaps_output(self):
        assert _has_ac_less_scope_gaps_instruction(ENDPOINT_ANALYZER_SKILL_PATH.read_text())

    def test_parent_orchestration_preserves_endpoint_gaps_disclosure_contract(self):
        instructions = _normalise_whitespace(CREATE_SKILL_PATH.read_text())

        assert "The endpoint analyzer owns disclosure" in instructions
        assert "Pass that analyzer output through unchanged" in instructions
        assert "collect its required `## Gaps` output into `TestPlanGaps.md` at Step 3.5" in instructions
        assert (
            "The parent must not be responsible for adding a concise entry in the analyzer `## Gaps` material "
            "passed to Step 3.5, inventing an objective, or using a free-text matcher to infer further exclusions."
            in instructions
        )
