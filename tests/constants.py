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

## 9. Test Environment Requirements

## 10. Appendix
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

## 9. Test Environment Requirements

## 10. Appendix
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

## 10. Appendix
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
