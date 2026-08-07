"""
Structural regression tests for skill templates.

Ensures skills/test-plan-create/test-plan-template.md stays in sync with
the deterministic validators that check LLM-generated output against it.
"""

import pytest

from scripts.utils.markdown_utils import extract_section, has_citation, parse_citations
from scripts.utils.schemas import _parse_template_headings, _require_headings
from scripts.validate import validate_interface_types, validate_structure
from tests.constants import REPO_ROOT

TEMPLATE_PATH = REPO_ROOT / "skills" / "test-plan-create" / "test-plan-template.md"

_SECTION_1_3_HEADING = "### 1.3 Test Objectives"


class TestTemplateSection4Structure:
    """Section 4 (Interfaces Under Test) in the template must match the deterministic validator."""

    def test_template_section4_has_no_priority_column(self):
        result = validate_interface_types(str(TEMPLATE_PATH))

        assert result["valid"] is True, f"Template Section 4 table does not match expected columns: {result}"
        assert result["header"] == ["Interface", "Type", "Purpose"]

    def test_template_has_no_bold_pseudo_headings(self):
        result = validate_structure(str(TEMPLATE_PATH))

        assert result["valid"] is True, f"Template structure invalid: {result}"
        assert result["pseudo_headings"] == [], f"Template contains bold pseudo-headings: {result['pseudo_headings']}"


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
