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

VALID_TEST_PLAN_DATA = {
    "feature": "Test Feature",
    "source_key": "RHAISTRAT-400",
    "version": "1.0.0",
    "status": "Draft",
    "last_updated": "2026-04-14",
    "author": "QE Team",
}

VALID_TEST_CASE_DATA = {
    "test_case_id": "TC-API-001",
    "source_key": "RHAISTRAT-400",
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
test_case_id: TC-API-001
priority: P0
title: Create notebook via API
---

## Objective
Test API endpoint.
"""

TC_WITH_TITLE_SECTION = """---
test_case_id: TC-API-001
priority: P0
---

## Title
Delete notebook via API

## Objective
Test deletion.
"""

TC_WITHOUT_TITLE = """---
test_case_id: TC-API-001
priority: P0
---

## Objective
No title section here.
"""

# Valid TestPlan.md content for validation tests
VALID_TESTPLAN_CONTENT = """---
source_key: RHAISTRAT-1507
feature: Notebook Spawning
version: 1.0.0
status: Draft
components:
  - Notebooks
  - AI Hub
---

## 1. Test Objectives
Test notebook spawning feature.

### 1.2 Scope
This feature enables users to spawn Jupyter notebooks.
"""

# Minimal valid TC file
MINIMAL_TC_CONTENT = """---
test_case_id: TC-API-001
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
TESTPLAN_E2E_ONLY = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 1. Executive Summary

### 1.3 Test Objectives

1. Verify model deployment via e2e system test (AC: "Users can deploy models")
2. Verify dashboard navigation via UI test (AC: "Dashboard shows model status")

## 2. Test Strategy

### 2.1 Test Levels

- **E2E System Testing** — end-to-end workflows through API and CLI
- **UI Testing** — dashboard interactions and form validation

### 2.2 Test Types

- **Positive Testing** — valid inputs
"""

# TestPlan.md with disallowed test levels (invalid scope)
TESTPLAN_BROAD_LEVELS = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 1. Executive Summary

### 1.3 Test Objectives

1. Verify API endpoint returns correct data
2. Verify UI renders correctly

## 2. Test Strategy

### 2.1 Test Levels

- **API Integration Testing** — REST endpoint testing against backend
- **Data Validation Testing** — data transformation, persistence
- **E2E System Testing** — end-to-end workflows
- **Functional Testing** — business logic, filtering

### 2.2 Test Types

- **Positive Testing** — valid inputs
"""

# TestPlan.md with no Section 2.1
TESTPLAN_NO_SECTION_21 = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 2. Test Strategy

### 2.2 Test Types

- **Positive Testing** — valid inputs
"""

# TestPlan.md with all AC citations present (valid)
TESTPLAN_AC_CITED = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 1. Executive Summary

### 1.3 Test Objectives

1. Verify model deployment works end-to-end (AC: "Users can deploy models from the catalog")
2. Verify dashboard shows status (AC: "Model status is visible in the dashboard")
3. Verify RBAC enforcement (AC: "Non-admin users cannot delete models")

## 2. Test Strategy
"""

# TestPlan.md with missing AC citations (invalid)
TESTPLAN_AC_MISSING = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 1. Executive Summary

### 1.3 Test Objectives

1. Verify model deployment works end-to-end (AC: "Users can deploy models")
2. Verify dashboard shows correct status
3. Verify RBAC enforcement for admin users (AC: "Admin users can manage all models")

## 2. Test Strategy
"""

# TestPlan.md with bullet-style objectives (not numbered — triggers format error)
TESTPLAN_AC_BULLET_FORMAT = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 1. Executive Summary

### 1.3 Test Objectives

- **Obj-1**: Verify catalog tile is visible (AC: "tile is visible")
- **Obj-2**: Verify dialog displays samples (AC: "samples displayed")

## 2. Test Strategy
"""

# TestPlan.md with no Section 1.3
TESTPLAN_NO_SECTION_13 = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 2. Test Strategy
"""

# TestPlan.md body content with proper structure (no frontmatter)
TESTPLAN_VALID_BODY = """
# Test Feature Test Plan

## 1. Executive Summary

### 1.1 Purpose

Test the feature.

### 1.2 Scope

In scope items.

### 1.3 Test Objectives

1. Verify something (AC: "acceptance criterion")

## 2. Test Strategy

### 2.1 Test Levels

- **E2E System Testing** — end-to-end workflows

### 2.2 Test Types

- **Positive Testing** — valid inputs

### 2.3 Test Priorities

- **P0 (Critical)** — core flows

## 3. Test Environment

## 4. Interfaces Under Test

## 7. Non-Functional Requirements

## 8. Risks and Mitigation

## 9. Appendix
"""

# TestPlan.md with bold-text pseudo-headings (invalid structure)
TESTPLAN_BOLD_HEADINGS = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 1. Executive Summary

### 1.1 Purpose

Test the feature.

### 1.2 Scope

In scope items.

### 1.3 Test Objectives

1. Verify something (AC: "acceptance criterion")

## 2. Test Strategy

### 2.1 Test Levels

- **E2E System Testing** — end-to-end workflows

### 2.2 Test Types

- **Positive Testing** — valid inputs

### 2.3 Test Priorities

- **P0 (Critical)** — core flows

## 3. Test Environment

## 4. Interfaces Under Test

## 7. Non-Functional Requirements

**Measurement Points:**

Some content here.

**Purpose:**

More content.

## 8. Risks and Mitigation

## 9. Appendix
"""

# TestPlan.md missing required sections
TESTPLAN_MISSING_SECTIONS = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 1. Executive Summary

### 1.1 Purpose

Test the feature.

## 2. Test Strategy

## 9. Appendix
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

# TestPlan.md with allowed TC categories in Section 5.2 (valid)
TESTPLAN_VALID_CATEGORIES = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 5. Test Cases

### 5.1 Test Case Summary

3 test cases total.

### 5.2 Test Case Naming Convention

Test cases follow the naming pattern: `TC-<CATEGORY>-<NUMBER>`

| Prefix | Meaning |
|--------|---------|
| TC-E2E | End-to-end user journey flows |
| TC-UI | Browser-based UI interaction flows |
| TC-NEG | Negative and error path journeys |
"""

# TestPlan.md with feature-area TC categories in Section 5.2 (invalid)
TESTPLAN_FEATURE_CATEGORIES = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 5. Test Cases

### 5.1 Test Case Summary

5 test cases total.

### 5.2 Test Case Naming Convention

Test cases follow the naming pattern: `TC-<CATEGORY>-<NUMBER>`

| Prefix | Meaning |
|--------|---------|
| TC-CSAF | Content safety filtering tests |
| TC-AUTH | Authentication and authorization tests |
| TC-TOPIC | Topical blocking tests |
| TC-E2E | End-to-end user journey flows |
"""

# TestPlan.md with no Section 5.2
TESTPLAN_NO_SECTION_52 = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 5. Test Cases

### 5.1 Test Case Summary

0 test cases.

## 6. E2E Test Scenarios
"""

# TestPlan.md with valid interface types in Section 4 (no Config)
TESTPLAN_VALID_INTERFACES = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 4. Interfaces Under Test

| Interface | Type | Purpose | Priority |
|-----------|------|---------|----------|
| `/v1/chat/completions` | REST | Chat inference | P0 |
| NemoGuardrails CRD | CRD | Guardrail configuration | P1 |
| Dashboard model page | UI | Model management | P0 |
"""

# TestPlan.md with Config-type entries in Section 4 (invalid)
TESTPLAN_CONFIG_INTERFACES = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

## 4. Interfaces Under Test

| Interface | Type | Purpose | Priority |
|-----------|------|---------|----------|
| `/v1/chat/completions` | REST | Chat inference | P0 |
| `config.yaml` | Config | Runtime configuration | P1 |
| `BASE_URL` env var | Config | Service endpoint | P1 |
| Dashboard model page | UI | Model management | P0 |
"""

# TestPlan.md with clean test infra (no SUT/dev tooling)
TESTPLAN_CLEAN_INFRA = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

### 3.1 Infrastructure & Configuration
- OpenShift 4.16+
- RHOAI 3.5 operator
- `KUBECONFIG` env var for cluster access
- CatalogSource for operator subscription

### 3.4 Test Tools
- oc/kubectl for cluster interaction
- curl for API testing
- pytest for test execution
"""

# TestPlan.md with local dev tooling leaked into infra sections
TESTPLAN_DEV_TOOLING_INFRA = """---
feature: Test Feature
source_key: RHAISTRAT-400
version: 1.0.0
status: Draft
last_updated: 2026-07-15
author: QE Team
---

# Test Feature Test Plan

### 3.1 Infrastructure & Configuration
- OpenShift 4.16+
- Local development runtime: Python 3.x with pip
- Container runtime (podman or docker)
- `KUBECONFIG` env var for cluster access

### 3.4 Test Tools
- oc/kubectl for cluster interaction
- pip install for local development
- docker-compose for local SUT setup
- Ollama for local LLM inference
"""

VALID_TC_CONTENT = """---
test_case_id: TC-API-001
source_key: RHAISTRAT-1519
priority: P0
status: Draft
last_updated: "2026-05-05"
automation_status: Not Started
---

# TC-API-001: Test title

**Objective**: Test objective

**Preconditions**:
- Precondition 1

**Test Steps**:
1. Step 1

**Expected Results**:
- Result 1
"""
