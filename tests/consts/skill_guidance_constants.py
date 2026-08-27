"""Constants for tests/unit/test_skill_guidance.py.

Paths and expected-keyword sets for the SKILL.md-content regression tests that guard the
live-review guidance added for issue #56 (opendatahub-tests#2187).
"""

from tests.constants import REPO_ROOT

SKILLS_DIR = REPO_ROOT / "skills"

GENERATE_SKILL = SKILLS_DIR / "test-plan-generate-test-file" / "SKILL.md"
SCORE_RUBRIC = SKILLS_DIR / "test-plan-score-test-function" / "prompts" / "score-test-function.md"
CALIBRATION_README = SKILLS_DIR / "test-plan-score-test-function" / "calibration" / "README.md"
CALIBRATION_POOR_PYTEST = SKILLS_DIR / "test-plan-score-test-function" / "calibration" / "core" / "poor-pytest-test.py"
CASE_IMPLEMENT_SKILL = SKILLS_DIR / "test-plan-case-implement" / "SKILL.md"

# Distinctive phrases the generation guidance must keep (Themes 1-7 + activation gate).
GENERATE_GUIDANCE_KEYWORDS = (
    "Activation gate",
    "false-green",
    "skip vs. fail",
    "Bounded loops",
    "Helper safety",
    "CWE-78",
    "skip_on_disconnected",
    "--strict-markers",
)

# The scorer rubric prompt must encode the new correctness/safety checks.
SCORE_RUBRIC_KEYWORDS = (
    "false green",
    "skip vs. fail",
    "probabilistic",
    "Bounded loops",
    "Helper safety",
    "CWE-78",
    "skip_on_disconnected",
    "always in scope",
)

# Keywords that must appear in BOTH the rubric prompt and the duplicated calibration README,
# so the two copies of the rubric stay in sync. Includes the tight-assertion criteria (exact type
# checks, finiteness, non-empty-before-indexing, all-candidates) so an omission in either copy fails.
RUBRIC_SYNC_KEYWORDS = (
    "false-green",
    "skip_on_disconnected",
    "unbounded loops",
    "shell injection",
    "numbers.Real",
    "NaN",
    "choices[0]",
    "**all** candidates",
)

# The extended poor calibration example must demonstrate the new anti-patterns.
CALIBRATION_POOR_KEYWORDS = (
    "false green",
    "pytest.skip",
    "unbounded loop",
    "CWE-78",
)

# The orchestrator must prompt for live validation and report unverified coverage.
CASE_IMPLEMENT_KEYWORDS = (
    "live validation",
    "Unverified coverage",
    "activation gate",
)
