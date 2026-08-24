"""
Test data constants for test-plan artifact tests.

Provides valid base data for each artifact type to use in tests.
"""

from pathlib import Path

# Repository root and common paths
REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Skill directory for testing (relative to repo root)
TEST_SKILL_DIR = str(Path.cwd() / "skills" / "test-plan-create")

VALID_TEST_CASE_DATA = {
    "test_case_id": "TC-E2E-001",
    "source_key": "RHAISTRAT-400",
    "objectives": [1],
    "priority": "P0",
    "status": "Draft",
    "last_updated": "2026-04-14",
}


VALID_TEST_GAPS_DATA = {
    "feature": "Test Feature",
    "source_key": "RHAISTRAT-400",
    "status": "Open",
    "gap_count": 3,
    "last_updated": "2026-04-14",
}


# TC file content templates for parser tests
TC_WITH_FRONTMATTER_TITLE = """---
test_case_id: TC-E2E-001
priority: P0
title: Create notebook via API
---

## Objective
Test API endpoint.
"""

TC_WITH_TITLE_SECTION = """---
test_case_id: TC-E2E-001
priority: P0
---

## Title
Delete notebook via API

## Objective
Test deletion.
"""

TC_WITHOUT_TITLE = """---
test_case_id: TC-E2E-001
priority: P0
---

## Objective
No title section here.
"""


# Minimal valid TC file
MINIMAL_TC_CONTENT = """---
test_case_id: TC-E2E-001
priority: P0
---

## Objective
Test something.

## Preconditions
- RHOAI cluster deployed

## Test Steps
1. Do something

## Expected Results
- Something happens
"""

# Test score file content
SCORE_FILE_READY = """**Verdict**: Ready
**Total Score**: 9/10

Quality assessment complete.
"""

SCORE_FILE_REVISE = """**Verdict**: Revise
**Total Score**: 5/10

### Issues Found
- Missing error handling
- Incomplete assertions

### Revision Needed
Add try/except blocks and assert all expected fields.
"""

# INDEX.md with table format (actual format from test-plan-create-cases)
INDEX_MD_TABLE_FORMAT = """# Test Case Index — Upgrade Validation

**Source**: [RHAISTRAT-1519](https://redhat.atlassian.net/browse/RHAISTRAT-1519)
**Test Plan**: [TestPlan.md](../TestPlan.md)

## Quick Stats

- **Total Test Cases**: 3
- **P0 (Critical)**: 2
- **P1 (High)**: 1

## Pipeline Trigger (TC-PIPE)

| Test Case | Title | Priority |
|-----------|-------|----------|
| [TC-PIPE-001](TC-PIPE-001.md) | Nightly release triggers validation | P0 |
| [TC-PIPE-002](TC-PIPE-002.md) | EA release triggers validation | P0 |
| [TC-PIPE-003](TC-PIPE-003.md) | Pipeline rejects unsupported path | P1 |
"""

# Test case with common preconditions for analyze_common_setup tests
TC_WITH_SHARED_PRECONDITIONS_1 = """---
test_case_id: TC-PIPE-001
priority: P0
category: Pipeline
status: Draft
last_updated: "2026-05-05"
automation_status: Not Started
---
# TC-PIPE-001: Nightly release triggers validation

**Objective**: Verify nightly release artifact triggers validation

**Preconditions**:
- Upgrade matrix configured with supported paths
- CI pipeline infrastructure connected to release system
- Valid kubeconfig with cluster access

**Test Steps**:
1. Produce nightly release artifact
2. Observe CI pipeline

**Expected Results**:
- Validation job triggered for each path
"""

TC_WITH_SHARED_PRECONDITIONS_2 = """---
test_case_id: TC-PIPE-002
priority: P0
category: Pipeline
status: Draft
last_updated: "2026-05-05"
automation_status: Not Started
---
# TC-PIPE-002: EA release triggers validation

**Objective**: Verify EA release artifact triggers validation

**Preconditions**:
- CI pipeline infrastructure connected to release system
- Release artifact storage accessible

**Test Steps**:
1. Produce EA release artifact
2. Observe CI pipeline

**Expected Results**:
- Validation job triggered
"""

TC_WITH_SHARED_PRECONDITIONS_3 = """---
test_case_id: TC-PIPE-003
priority: P1
category: Pipeline
status: Draft
last_updated: "2026-05-05"
automation_status: Not Started
---
# TC-PIPE-003: Pipeline rejects unsupported path

**Objective**: Verify pipeline rejects unsupported upgrade paths

**Preconditions**:
- Upgrade matrix configured with supported paths

**Test Steps**:
1. Attempt unsupported upgrade path
2. Check pipeline response

**Expected Results**:
- Pipeline rejects the request
"""


# STRAT parser test data — Jira wiki markup variations

STRAT_AC_NUMBERED_LIST = (
    "h3. Acceptance Criteria (Proposed — requires PM/Engineering validation)\n\n"
    "# Given a user opens a session,\n"
    "\n"
    "   when the page loads, then a tile is visible, measured by rendering.\n"
    "\n"
    "# Given a user clicks the tile,\n"
    "\n"
    "   when the dialog opens, then samples are shown, measured by card count.\n"
    "\n"
    "# Given the dialog is open,\n"
    "\n"
    "   when the user selects a filter, then results update, measured by count.\n"
    "\n"
    "h3. Effort Estimate\n"
)

STRAT_AC_NUMBERED_SINGLE_LINE = (
    "h3. Acceptance Criteria\n\n"
    "# Given X, when Y, then Z, measured by W.\n"
    "\n"
    "# Given A, when B, then C, measured by D.\n"
    "\n"
    "h3. Effort Estimate\n"
)

STRAT_AC_NUMBERED_MULTI_PARAGRAPH = (
    "h3. Acceptance Criteria\n\n"
    "# Given a user registers a vector store,\n"
    "\n"
    "   when the registration completes,\n"
    "\n"
    "   then the store appears in the catalog, measured by API response.\n"
    "\n"
    "# Given a user deletes a vector store,\n"
    "\n"
    "   when confirmed, then the store is removed.\n"
    "\n"
    "h3. Effort Estimate\n"
)

STRAT_OOS_PLAIN_TEXT = (
    "h3. Out-of-Scope\n\n"
    "* Custom management UI in the Dashboard (catalog is within JupyterLab only)\n"
    "* Remote catalog server or registry (V1 uses local paths only)\n"
    "* Sample authoring or editing tools within the dialog\n"
    "* Automatic updates or versioning across restarts\n"
    "* Usage telemetry\n"
    "\nh3. Acceptance Criteria\n"
)

STRAT_OOS_EM_DASH = (
    "h3. Out-of-Scope\n\n* *Backend API*—delivered by RHAISTRAT-2281, not this strategy\n\nh3. Acceptance Criteria\n"
)

STRAT_OOS_MIXED = (
    "h3. Out-of-Scope\n\n"
    "* *Tabbed serving admin UI*: Consolidating pages into a single tabbed interface\n"
    "* Data ingestion, ETL, or data transformation UI\n"
    "* *Rich form rendering*—deferred for TP\n"
    "\nh3. Acceptance Criteria\n"
)

STRAT_AC_NUMBERED_NO_BLANK_LINES = (
    "h3. Acceptance Criteria\n\n"
    "# Given a user opens a session, when the page loads, then a tile is visible.\n"
    "# Given a user clicks the tile, when the dialog opens, then samples are shown.\n"
    "# Given the dialog is open, when the user selects a filter, then results update.\n"
    "\nh3. Effort Estimate\n"
)

STRAT_AC_STAR_BULLETS_NO_BLANK_LINES = (
    "h3. Acceptance Criteria (Proposed -- requires PM/Engineering validation)\n\n"
    "* Given a user opens the form, when they submit valid input, then the entry is created\n"
    "* Given a user submits invalid input, when validation runs, then an error is shown\n"
    "* Given a duplicate name is submitted, when validation runs, then the request is rejected\n"
    "\nh3. Effort Estimate\n"
)

STRAT_NFR_WRAPPED_BULLET = (
    "h3. Non-Functional Requirements\n\n"
    "* *Security*: Registration is namespace-scoped; the gen-ai BFF enforces\n"
    "namespace isolation via the user token's RBAC permissions, consistent\n"
    "with all other BFF endpoints.\n"
    "* a stray bullet with no category\n"  # not the "* *Cat*: text" form → must not merge into Security
    "* *Performance*: Connectivity validation enforces a configurable timeout.\n"
    "\nh3. Out-of-Scope\n"
)

STRAT_TESTABILITY_FOLDED_INTO_AC = (
    "h3. Acceptance Criteria\n\n"
    "# Given a user opens a session, when the page loads, then a tile is visible.\n"
    "# Given a user clicks the tile, when the dialog opens, then samples are shown.\n"
    "\nh3. Testability: Additional Acceptance Criteria\n\n"
    "The following edge cases should be covered as acceptance criteria:\n\n"
    "# *Unverified status*: Given a provider type with inconclusive connectivity, "
    "when validation runs, then the status is Unverified.\n"
    "# *Malformed secret*: Given a secret exists but is missing the expected credential key, "
    "when the user submits registration, then a clear error is returned.\n"
    "\nh3. Effort Estimate\n"
)

STRAT_TESTABILITY_DEDUPED_AGAINST_MAIN_AC = (
    "h3. Acceptance Criteria\n\n"
    "# Given a user clicks the tile, when the dialog opens, then samples are shown.\n"
    "\nh3. Testability: Additional Acceptance Criteria\n\n"
    "# *Duplicate*: Given a user clicks the tile, when the dialog opens, then samples are shown.\n"
    "# *Unverified status*: Given a provider type with inconclusive connectivity, "
    "when validation runs, then the status is Unverified.\n"
    "\nh3. Effort Estimate\n"
)

# Main AC section is mandatory — Testability items must not be treated as ACs on their own.
STRAT_TESTABILITY_WITHOUT_MAIN_AC_SECTION = (
    "h3. Testability: Additional Acceptance Criteria\n\n"
    "# *Unverified status*: Given a provider type with inconclusive connectivity, "
    "when validation runs, then the status is Unverified.\n"
    "\nh3. Effort Estimate\n"
)


VALID_TC_CONTENT = """---
test_case_id: TC-E2E-001
source_key: RHAISTRAT-400
objectives: [1]
priority: P0
status: Draft
last_updated: "2026-05-05"
automation_status: Not Started
---

# TC-E2E-001: Test title

**Objective**: Test objective

**Preconditions**:
- Precondition 1

**Test Steps**:
1. Step 1

**Expected Results**:
- Result 1
"""
