"""
Test data constants for integration tests.

TC file content strings for testing tc_parser.py
"""

VALID_COMPLETE_TC = """---
test_case_id: TC-API-001
strat_key: RHAISTRAT-1262
priority: P0
status: Draft
---
# TC-API-001: Test Title

**Objective**: Verify that the API returns correct metadata

**Preconditions**:
- RHOAI cluster deployed
- Model catalog API available

**Test Steps**:
1. Send GET request to API endpoint
2. Verify response status is 200
3. Parse JSON response

**Expected Results**:
- Response status is 200
- JSON contains required fields

**Test Data**:
```json
{"model_id": "test"}
```

**Notes**: Additional context
"""

TC_WITH_MULTILINE_ITEMS = """---
test_case_id: TC-API-001
---
**Objective**: Test multiline

**Preconditions**:
- Requirement that spans
  multiple lines with indentation
- Another requirement

**Test Steps**:
1. Step one that also
   spans multiple lines
2. Step two

**Expected Results**:
- Expected result spanning
  multiple lines
"""

TC_WITH_EMPTY_LINES = """---
test_case_id: TC-API-001
---
**Objective**: Test

**Preconditions**:
- Item 1

- Item 2

- Item 3

**Test Steps**:
1. Step 1

2. Step 2

**Expected Results**:
- Result
"""

TC_MISSING_OBJECTIVE = """---
test_case_id: TC-API-001
---
**Preconditions**:
- Req

**Test Steps**:
1. Step

**Expected Results**:
- Result
"""

TC_EMPTY_PRECONDITIONS = """---
test_case_id: TC-API-001
---
**Objective**: Test

**Preconditions**:

**Test Steps**:
1. Step

**Expected Results**:
- Result
"""

TC_MISSING_TEST_STEPS = """---
test_case_id: TC-API-001
---
**Objective**: Test

**Preconditions**:
- Req

**Expected Results**:
- Result
"""

TC_MISSING_EXPECTED_RESULTS = """---
test_case_id: TC-API-001
---
**Objective**: Test

**Preconditions**:
- Req

**Test Steps**:
1. Step
"""

TC_WITH_OPTIONAL_SECTIONS = """---
test_case_id: TC-API-001
---
**Objective**: Test

**Preconditions**:
- Req

**Test Steps**:
1. Step

**Expected Results**:
- Result

**Test Data**:
```json
{"key": "value"}
```

**Expected Response**:
```json
{"status": "ok"}
```

**Validation**:
- Database check

**Notes**: Some notes here
"""

TC_WITH_BULLET_TEST_STEPS = """---
test_case_id: TC-API-001
---
**Objective**: Test

**Preconditions**:
- Req

**Test Steps**:
- Step 1 (wrong format - should be numbered)
- Step 2

**Expected Results**:
- Result
"""

# ─── TestPlan.md test data for repo_discovery tests ─────────────────────────

TESTPLAN_WITH_ENDPOINTS = """---
feature: Test Feature
strat_key: RHAISTRAT-1262
---
### 4: Endpoints/Methods Under Test

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/notebooks | GET | List notebooks |
| /api/v1/models | POST | Create model |
"""

TESTPLAN_WITH_SCOPE_COMPONENTS = """---
feature: Test Feature
---
### 1.2 Scope

This feature covers the dashboard UI and model-registry integration.
"""

TESTPLAN_FOR_TC_PRECONDITIONS = """---
feature: Test
---
### 1.2 Scope
Test scope

### 4: Endpoints
None
"""

TC_WITH_COMPONENT_MENTIONS = """---
test_case_id: TC-API-001
priority: P0
---
**Objective**: Test

**Preconditions**:
- RHOAI cluster with notebooks deployed
- Model-registry available

**Test Steps**:
1. Test step

**Expected Results**:
- Result
"""

TESTPLAN_WITH_DUPLICATES = """---
feature: Test
---
### 1.2 Scope
Dashboard and notebooks

### 4: Endpoints
/api/v1/notebooks
/api/v1/dashboard/status
"""
