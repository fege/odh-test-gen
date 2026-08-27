"""Regression contract for README quality-evidence descriptions."""

import re

from tests.constants import REPO_ROOT


def test_readme_describes_quality_evidence_inputs_and_all_persisted_gate_caps():
    readme = (REPO_ROOT / "README.md").read_text()

    assert "validate_quality_evidence.py" in readme
    assert "scope coverage and actionability evidence" in readme.casefold()
    assert "scope_coverage_result" in readme
    assert "actionability_result" in readme
    assert "cap Scope Fidelity/Specificity/Actionability" in readme
    assert "enforce_citation_gate.py # Deterministically cap Scope Fidelity/Specificity/Actionability" in readme
    assert re.search(
        r"cap_scope_fidelity\.py\s+#.*stateless.*Scope Fidelity/Specificity/Actionability",
        readme,
        flags=re.IGNORECASE,
    )
