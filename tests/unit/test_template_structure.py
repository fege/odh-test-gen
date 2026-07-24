"""
Structural regression tests for skill templates.

Ensures skills/test-plan-create/test-plan-template.md stays in sync with
the deterministic validators that check LLM-generated output against it.
"""

from scripts.validate import validate_interface_types
from tests.constants import REPO_ROOT

TEMPLATE_PATH = REPO_ROOT / "skills" / "test-plan-create" / "test-plan-template.md"


class TestTemplateSection4Structure:
    """Section 4 (Interfaces Under Test) in the template must match the deterministic validator."""

    def test_template_section4_has_no_priority_column(self):
        result = validate_interface_types(str(TEMPLATE_PATH))

        assert result["valid"] is True, f"Template Section 4 table does not match expected columns: {result}"
        assert result["header"] == ["Interface", "Type", "Purpose"]
