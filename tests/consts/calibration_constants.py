"""Constants for scripts/load_calibration.py tests."""

from tests.constants import REPO_ROOT

REVIEW_CALIBRATION_DIR = REPO_ROOT / "skills" / "test-plan-review" / "calibration"
FUNCTION_CALIBRATION_DIR = REPO_ROOT / "skills" / "test-plan-score-test-function" / "calibration"
REVIEW_CALIBRATION_CORE = REVIEW_CALIBRATION_DIR / "core"
FUNCTION_CALIBRATION_CORE = FUNCTION_CALIBRATION_DIR / "core"
FUNCTION_CALIBRATION_UI = FUNCTION_CALIBRATION_DIR / "ui"

PLAN_KAGENTI_FILENAME = "01-kagenti-agent-templates.md"
PLAN_CALIBRATION_PHRASE = "RHAISTRAT-1290"
MIN_PLAN_CALIBRATION_FILES = 3

FUNCTION_CORE_PYTEST_GLOB = "*pytest*"
FUNCTION_CORE_FORBIDDEN_GLOBS = ("*.go", "*.spec.tsx")

PLAN_CORE_FIRST = "01-first.md"
PLAN_CORE_LATER = "02-later.md"
PLAN_CORE_FIRST_BODY = "first core example"
PLAN_CORE_LATER_BODY = "later core example"
PLAN_CORE_FILES = {
    PLAN_CORE_LATER: f"{PLAN_CORE_LATER_BODY}\n",
    PLAN_CORE_FIRST: f"{PLAN_CORE_FIRST_BODY}\n",
}

README_FILENAME = "README.md"
README_BODY = "do not load this README"

TEAM_NAME_AI_HUB = "ai_hub"
TEAM_EXTRA_FILENAME = "team-extra.md"
TEAM_EXTRA_BODY = "ai_hub team example"

DUP_FILENAME = "shared.md"
DUP_CORE_BODY = "core copy of shared"
DUP_TEAM_BODY = "team copy of shared must be omitted"

MISSING_TEAM_NAME = "nonexistent"

# Outside-calibration fixture layout; unique body must never load.
ESCAPE_OUTSIDE_DIRNAME = "outside"
ESCAPE_FILENAME = "escaped-calibration.md"
ESCAPE_BODY = "escaped team file must never appear in calibration_text"
SYMLINK_OUTSIDE_BODY = "core symlink target outside calibration must never appear in calibration_text"
TEAM_EMPTY = ""
TEAM_WHITESPACE = " "

FRAMEWORK_PYTEST_GOOD = "good-pytest-test.py"
FRAMEWORK_PYTEST_POOR = "poor-pytest-test.py"
FRAMEWORK_GO = "good-go-test.go"
FRAMEWORK_CYPRESS = "good-cypress-test.cy.ts"
FRAMEWORK_CYPRESS_POOR = "poor-cypress-test.cy.ts"
FRAMEWORK_TYPESCRIPT = "good-typescript-test.spec.tsx"
PYTEST_CORE_FILES = {
    FRAMEWORK_PYTEST_GOOD: "def test_good():\n    pass\n",
    FRAMEWORK_PYTEST_POOR: "def test_poor():\n    pass\n",
}
FRAMEWORK_CORE_FILES = {
    **PYTEST_CORE_FILES,
    FRAMEWORK_GO: "package calibration\n",
    FRAMEWORK_CYPRESS: "describe('cal', () => {})\n",
    FRAMEWORK_TYPESCRIPT: "export {}\n",
}
# Substring "go" matches "good-pytest-test.py"; token match must keep only the .go file.
FRAMEWORK_GO_TOKEN = "go"
# generate-test-file may pass this; pytest-only core has no matching files.
FRAMEWORK_UNMATCHED = "playwright"
GO_AND_PYTEST_CORE_FILES = {
    FRAMEWORK_PYTEST_GOOD: PYTEST_CORE_FILES[FRAMEWORK_PYTEST_GOOD],
    FRAMEWORK_GO: FRAMEWORK_CORE_FILES[FRAMEWORK_GO],
}
INVALID_UTF8_CORE_FILENAME = "invalid-utf8.md"
UI_CYPRESS_FILES = {
    FRAMEWORK_CYPRESS: "describe('good', () => {})\n",
    FRAMEWORK_CYPRESS_POOR: "describe('poor', () => {})\n",
}
# Substring "go" matches "good-pytest-test.py"; use these for real-tree filename checks.
NON_PYTEST_PATH_MARKERS = ("-go-", ".go", "cypress", "typescript", ".tsx")
UI_OVERLAY_SOURCE = "ui"
UI_CYPRESS_GOOD_PATH = f"{UI_OVERLAY_SOURCE}/{FRAMEWORK_CYPRESS}"
UI_TEAM_FILES = {UI_OVERLAY_SOURCE: UI_CYPRESS_FILES}
