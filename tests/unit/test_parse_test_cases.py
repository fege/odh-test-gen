"""Unit tests for scripts/parse_test_cases.py"""

import json
import pytest

from scripts.parse_test_cases import parse_test_cases
from tests.constants import VALID_TEST_CASE_DATA


def test_parses_single_tc(tmp_path):
    """Should parse a single TC file into structured data."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    (tc_dir / "TC-API-001.md").write_text(f"""---
test_case_id: {VALID_TEST_CASE_DATA['test_case_id']}
source_key: {VALID_TEST_CASE_DATA['source_key']}
priority: {VALID_TEST_CASE_DATA['priority']}
status: {VALID_TEST_CASE_DATA['status']}
last_updated: "{VALID_TEST_CASE_DATA['last_updated']}"
automation_status: Not Started
placement_location: component
level: integration
---
# Verify API endpoint

**Objective**: Test the API endpoint works

**Preconditions**:
- Cluster is running
- API is deployed

**Test Steps**:
1. Call the API
2. Verify response

**Expected Results**:
- Returns 200 OK
- Response contains expected data
""")

    result = parse_test_cases(str(tmp_path), ["TC-API-001"])
    data = json.loads(result)

    assert len(data) == 1
    assert data[0]["test_case_id"] == "TC-API-001"
    assert data[0]["objective"] == "Test the API endpoint works"
    assert len(data[0]["preconditions"]) == 2
    assert len(data[0]["test_steps"]) == 2
    assert len(data[0]["expected_results"]) == 2


def test_parses_multiple_tcs(tmp_path):
    """Should parse multiple TC files."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    for i in range(1, 3):
        (tc_dir / f"TC-API-00{i}.md").write_text(f"""---
test_case_id: TC-API-00{i}
source_key: RHAISTRAT-400
priority: P0
status: Draft
last_updated: "2026-05-05"
automation_status: Not Started
---
# Test {i}

**Objective**: Test objective {i}

**Preconditions**:
- Precondition

**Test Steps**:
1. Step {i}

**Expected Results**:
- Result {i}
""")

    result = parse_test_cases(str(tmp_path), ["TC-API-001", "TC-API-002"])
    data = json.loads(result)

    assert len(data) == 2
    assert data[0]["test_case_id"] == "TC-API-001"
    assert data[1]["test_case_id"] == "TC-API-002"


def test_missing_tc_file(tmp_path):
    """Should raise error if TC file doesn't exist."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="TC-MISSING.md not found"):
        parse_test_cases(str(tmp_path), ["TC-MISSING"])
