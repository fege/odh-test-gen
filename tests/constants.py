"""
Test data constants for test-plan artifact tests.

Provides valid base data for each artifact type to use in tests.
"""

from pathlib import Path

from scripts.utils.schemas import TEMPLATE_HEADINGS

# Repository root and common paths
REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Skill directory for testing (relative to repo root)
TEST_SKILL_DIR = str(Path.cwd() / "skills" / "test-plan-create")

VALID_TEST_PLAN_DATA = {
    "feature": "Test Feature",
    "source_key": "RHAISTRAT-400",
    "version": "1.0.0",
    "status": "Draft",
    "last_updated": "2026-04-14",
    "author": "QE Team",
}

VALID_TEST_CASE_DATA = {
    "test_case_id": "TC-E2E-001",
    "source_key": "RHAISTRAT-400",
    "objectives": [1],
    "priority": "P0",
    "status": "Draft",
    "last_updated": "2026-04-14",
}

VALID_TEST_PLAN_REVIEW_DATA = {
    "feature": "Test Feature",
    "source_key": "RHAISTRAT-400",
    "score": 8,
    "pass": True,
    "verdict": "Ready",
    "scores": {
        "specificity": 2,
        "grounding": 2,
        "scope_fidelity": 1,
        "actionability": 2,
        "consistency": 1,
    },
    "auto_revised": False,
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

# Valid TestPlan.md content for validation tests
VALID_TESTPLAN_CONTENT = f"""---
source_key: RHAISTRAT-1507
feature: Notebook Spawning
version: 1.0.0
status: Draft
components:
  - Notebooks
  - AI Hub
---

{TEMPLATE_HEADINGS["1"]}
Test notebook spawning feature.

{TEMPLATE_HEADINGS["1.2"]}
This feature enables users to spawn Jupyter notebooks.
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

# Valid TC file with all required fields
# TestPlan.md with only e2e/UI test levels (valid scope)
TESTPLAN_E2E_ONLY = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["1"]}

{TEMPLATE_HEADINGS["1.3"]}

1. Verify model deployment via e2e system test (AC: "Users can deploy models")
2. Verify dashboard navigation via UI test (AC: "Dashboard shows model status")

{TEMPLATE_HEADINGS["2"]}

{TEMPLATE_HEADINGS["2.1"]}

- **E2E System Testing** — end-to-end workflows through API and CLI
- **UI Testing** — dashboard interactions and form validation

{TEMPLATE_HEADINGS["2.2"]}

- **Positive Testing** — valid inputs
"""

# TestPlan.md with disallowed test levels (invalid scope)
TESTPLAN_BROAD_LEVELS = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["1"]}

{TEMPLATE_HEADINGS["1.3"]}

1. Verify API endpoint returns correct data
2. Verify UI renders correctly

{TEMPLATE_HEADINGS["2"]}

{TEMPLATE_HEADINGS["2.1"]}

- **API Integration Testing** — REST endpoint testing against backend
- **Data Validation Testing** — data transformation, persistence
- **E2E System Testing** — end-to-end workflows
- **Functional Testing** — business logic, filtering

{TEMPLATE_HEADINGS["2.2"]}

- **Positive Testing** — valid inputs
"""

# TestPlan.md with no Section 2.1
TESTPLAN_NO_SECTION_21 = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["2"]}

{TEMPLATE_HEADINGS["2.2"]}

- **Positive Testing** — valid inputs
"""

# TestPlan.md with all AC citations present (valid)
# Objective 1's (AC: ...) is wrapped onto a continuation line — the parser must join
# continuation lines before checking, or it reads objective 1 as uncited.
TESTPLAN_AC_CITED = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["1"]}

{TEMPLATE_HEADINGS["1.3"]}

1. Verify model deployment works end-to-end
   (AC: #1 — "Users can deploy models from the catalog")
2. Verify dashboard shows status (AC: #2 — "Model status is visible in the dashboard")
3. Verify RBAC enforcement (AC: #3 — "Non-admin users cannot delete models")

{TEMPLATE_HEADINGS["2"]}
"""

# TestPlan.md with missing AC citations (invalid)
TESTPLAN_AC_MISSING = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["1"]}

{TEMPLATE_HEADINGS["1.3"]}

1. Verify model deployment works end-to-end (AC: #1 — "Users can deploy models")
2. Verify dashboard shows correct status
3. Verify RBAC enforcement for admin users (AC: #3 — "Admin users can manage all models")

{TEMPLATE_HEADINGS["2"]}
"""

# TestPlan.md with bullet-style objectives (not numbered — triggers format error)
TESTPLAN_AC_BULLET_FORMAT = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["1"]}

{TEMPLATE_HEADINGS["1.3"]}

- **Obj-1**: Verify catalog tile is visible (AC: "tile is visible")
- **Obj-2**: Verify dialog displays samples (AC: "samples displayed")

{TEMPLATE_HEADINGS["2"]}
"""

# TestPlan.md with no Section 1.3
TESTPLAN_NO_SECTION_13 = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["2"]}
"""

# TestPlan.md body content with proper structure (no frontmatter)
TESTPLAN_VALID_BODY = f"""
# Test Feature Test Plan

{TEMPLATE_HEADINGS["1"]}

{TEMPLATE_HEADINGS["1.1"]}

Test the feature.

{TEMPLATE_HEADINGS["1.2"]}

In scope items.

{TEMPLATE_HEADINGS["1.3"]}

1. Verify something (AC: #1 — "acceptance criterion")

{TEMPLATE_HEADINGS["2"]}

{TEMPLATE_HEADINGS["2.1"]}

- **E2E System Testing** — end-to-end workflows

{TEMPLATE_HEADINGS["2.2"]}

- **Positive Testing** — valid inputs

{TEMPLATE_HEADINGS["2.3"]}

- **P0 (Critical)** — core flows

{TEMPLATE_HEADINGS["3"]}

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | List models |

{TEMPLATE_HEADINGS["7"]}

{TEMPLATE_HEADINGS["8"]}

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | | |
| `/v1/models` | | |
"""

# TestPlan.md with bold-text pseudo-headings (invalid structure)
TESTPLAN_BOLD_HEADINGS = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["1"]}

{TEMPLATE_HEADINGS["1.1"]}

Test the feature.

{TEMPLATE_HEADINGS["1.2"]}

In scope items.

{TEMPLATE_HEADINGS["1.3"]}

1. Verify something (AC: #1 — "acceptance criterion")

{TEMPLATE_HEADINGS["2"]}

{TEMPLATE_HEADINGS["2.1"]}

- **E2E System Testing** — end-to-end workflows

{TEMPLATE_HEADINGS["2.2"]}

- **Positive Testing** — valid inputs

{TEMPLATE_HEADINGS["2.3"]}

- **P0 (Critical)** — core flows

{TEMPLATE_HEADINGS["3"]}

{TEMPLATE_HEADINGS["4"]}

{TEMPLATE_HEADINGS["7"]}

**Measurement Points:**

Some content here.

**Purpose:**

More content.

{TEMPLATE_HEADINGS["8"]}

{TEMPLATE_HEADINGS["9"]}
"""

# TestPlan.md missing required sections
TESTPLAN_MISSING_SECTIONS = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["1"]}

{TEMPLATE_HEADINGS["1.1"]}

Test the feature.

{TEMPLATE_HEADINGS["2"]}

{TEMPLATE_HEADINGS["9"]}
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

# TestPlan.md with allowed TC categories in Section 5.2 (valid)
TESTPLAN_VALID_CATEGORIES = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["5"]}

{TEMPLATE_HEADINGS["5.1"]}

3 test cases total.

{TEMPLATE_HEADINGS["5.2"]}

Test cases follow the naming pattern: `TC-<CATEGORY>-<NUMBER>`

| Prefix | Meaning |
|--------|---------|
| TC-E2E | End-to-end user journey flows |
| TC-UI | Browser-based UI interaction flows |
| TC-NEG | Negative and error path journeys |
"""

# TestPlan.md with feature-area TC categories in Section 5.2 (invalid)
TESTPLAN_FEATURE_CATEGORIES = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["5"]}

{TEMPLATE_HEADINGS["5.1"]}

5 test cases total.

{TEMPLATE_HEADINGS["5.2"]}

Test cases follow the naming pattern: `TC-<CATEGORY>-<NUMBER>`

| Prefix | Meaning |
|--------|---------|
| TC-CSAF | Content safety filtering tests |
| TC-AUTH | Authentication and authorization tests |
| TC-TOPIC | Topical blocking tests |
| TC-E2E | End-to-end user journey flows |
"""

# TestPlan.md with no Section 5.2
TESTPLAN_NO_SECTION_52 = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["5"]}

{TEMPLATE_HEADINGS["5.1"]}

0 test cases.

{TEMPLATE_HEADINGS["6"]}
"""

# TestPlan.md with valid interface types in Section 4 (no Config)
TESTPLAN_VALID_INTERFACES = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| NemoGuardrails CRD | CRD | Guardrail configuration |
| Dashboard model page | UI | Model management |
"""

# Section 4 header row has a blank cell — the validator must report the real header row
# (above the separator), not silently promote the first data row to "header".
TESTPLAN_INTERFACE_TYPES_BLANK_HEADER_CELL = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type |  |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
"""

# TestPlan.md with Config-type entries in Section 4 (invalid)
TESTPLAN_CONFIG_INTERFACES = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `config.yaml` | Config | Runtime configuration |
| `BASE_URL` env var | Config | Service endpoint |
| Dashboard model page | UI | Model management |
"""

# TestPlan.md where Section 9.2 and 6.2 fully cover Section 4 interfaces
# Full coverage, but Section 4 uses bold/plain formatting while 6.2/9.2 use backticks —
# normalization must still match them (regression for exact-string-equality false failures).
TESTPLAN_INTERFACE_COVERAGE_FULL = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| **/v1/chat/completions** | REST | Chat inference |
| /v1/models | REST | List models |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| `/v1/chat/completions` | TC-E2E-001 |
| `/v1/models` | TC-E2E-002 |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | TC-E2E-001 | |
| `/v1/models` | TC-E2E-002 | |
"""

# TestPlan.md where Section 9.2 is missing an interface from Section 4
TESTPLAN_INTERFACE_COVERAGE_MISSING_9_2 = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | List models |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| | |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | TC-E2E-001 | |
"""

# TestPlan.md where Section 6.2 is populated but missing an interface from Section 4
TESTPLAN_INTERFACE_COVERAGE_MISSING_6_2 = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | List models |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| `/v1/chat/completions` | TC-E2E-001 |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | | |
| `/v1/models` | | |
"""

# TestPlan.md where Section 6.2 is still the pre-create-cases placeholder (skip check)
TESTPLAN_INTERFACE_COVERAGE_PLACEHOLDER_6_2 = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | List models |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| | |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | TC-E2E-001 | |
| `/v1/models` | TC-E2E-002 | |
"""

# TestPlan.md where an interface is marked "pending details" in Section 4 and is
# absent from both Section 6.2 and 9.2 — it must be excluded from the missing lists.
TESTPLAN_INTERFACE_COVERAGE_PENDING = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | pending details |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| `/v1/chat/completions` | TC-E2E-001 |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | TC-E2E-001 | |
"""

# TestPlan.md where Section 9.2 lists the interface but its Test Cases cell is blank
TESTPLAN_INTERFACE_COVERAGE_EMPTY_9_2_CELL = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | List models |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| `/v1/chat/completions` | TC-E2E-001 |
| `/v1/models` | TC-E2E-002 |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | TC-E2E-001 | |
| `/v1/models` | | |
"""

# TestPlan.md where Section 6.2 lists the interface but its E2E Scenarios cell is blank
TESTPLAN_INTERFACE_COVERAGE_EMPTY_6_2_CELL = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | List models |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| `/v1/chat/completions` | TC-E2E-001 |
| `/v1/models` | |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | TC-E2E-001 | |
| `/v1/models` | TC-E2E-002 | |
"""

# TestPlan.md where Section 9.2's Test Cases cell is a non-informative placeholder, not a real TC ID
TESTPLAN_INTERFACE_COVERAGE_PLACEHOLDER_TC_CELL = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | List models |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| `/v1/chat/completions` | TC-E2E-001 |
| `/v1/models` | TC-E2E-002 |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | TC-E2E-001 | |
| `/v1/models` | TBD | |
"""

# TestPlan.md where Section 6.2's E2E Scenarios cell is a non-informative placeholder, not a real TC ID
TESTPLAN_INTERFACE_COVERAGE_PLACEHOLDER_SCENARIO_CELL = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["4"]}

| Interface | Type | Purpose |
|-----------|------|---------|
| `/v1/chat/completions` | REST | Chat inference |
| `/v1/models` | REST | List models |

{TEMPLATE_HEADINGS["6"]}

{TEMPLATE_HEADINGS["6.2"]}

| Interface (from Section 4) | E2E Scenarios |
|----------------------------|---------------|
| `/v1/chat/completions` | TC-E2E-001 |
| `/v1/models` | - |

{TEMPLATE_HEADINGS["9"]}

{TEMPLATE_HEADINGS["9.2"]}

| Interface | Test Cases | Coverage |
|-----------|------------|----------|
| `/v1/chat/completions` | TC-E2E-001 | |
| `/v1/models` | TC-E2E-002 | |
"""

# TestPlan.md with clean test infra (no SUT/dev tooling)
TESTPLAN_CLEAN_INFRA = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["3.1"]}
- OpenShift 4.16+
- RHOAI 3.5 operator
- `KUBECONFIG` env var for cluster access
- CatalogSource for operator subscription

{TEMPLATE_HEADINGS["3.4"]}
- oc/kubectl for cluster interaction
- curl for API testing
- pytest for test execution
"""

# TestPlan.md with local dev tooling leaked into infra sections
TESTPLAN_DEV_TOOLING_INFRA = f"""---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

{TEMPLATE_HEADINGS["3.1"]}
- OpenShift 4.16+
- Local development runtime: Python 3.x with pip
- Container runtime (podman or docker)
- `KUBECONFIG` env var for cluster access

{TEMPLATE_HEADINGS["3.4"]}
- oc/kubectl for cluster interaction
- pip install for local development
- docker-compose for local SUT setup
- Ollama for local LLM inference
"""

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
