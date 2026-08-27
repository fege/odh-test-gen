"""Regression contracts for Actionability 2/2 documentation guidance."""

import pytest

from tests.constants import REPO_ROOT


_CANONICAL_TBD_RESOLUTION = (
    "TBD — Resolution: {concrete action} from/with/by/before/after/using {named source or timing}"
)

_ACTIONABILITY_GUIDANCE = (
    (
        REPO_ROOT / "skills" / "test-plan-review" / "SKILL.md",
        'Leave TBD as plain "TBD"',
    ),
    (
        REPO_ROOT / "skills" / "test-plan-review" / "calibration" / "core" / "03-amd-mi350p-model-serving.md",
        "TBD-with-reason",
    ),
    (
        REPO_ROOT / "docs" / "human-review-guide.md",
        "marked TBD with rationale",
    ),
)


class TestActionabilityDocumentationContract:
    @pytest.mark.parametrize("path, disallowed_guidance", _ACTIONABILITY_GUIDANCE)
    def test_actionability_two_guidance_requires_canonical_tbd_resolution(self, path, disallowed_guidance):
        guidance = path.read_text()

        assert "actionability == 2" in guidance
        assert _CANONICAL_TBD_RESOLUTION in guidance
        assert disallowed_guidance not in guidance
