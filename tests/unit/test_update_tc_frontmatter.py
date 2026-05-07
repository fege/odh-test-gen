"""
Unit tests for scripts/update_tc_frontmatter.py

Tests bulk TC frontmatter updates for automation tracking.
"""

import json

from scripts.update_tc_frontmatter import update_tc_frontmatter
from scripts.utils.frontmatter_utils import read_frontmatter
from tests.constants import TC_WITH_NON_ALPHABETICAL_FRONTMATTER


def test_preserves_frontmatter_field_order(tmp_path):
    """
    Should preserve frontmatter field order (not alphabetize).
    """
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    tc_file = tc_dir / "TC-API-001.md"
    tc_file.write_text(TC_WITH_NON_ALPHABETICAL_FRONTMATTER)

    # Update automation_status field (must use valid enum value from schema)
    updates = [{
        "tc_id": "TC-API-001",
        "automation_status": "Complete"
    }]

    result_json = update_tc_frontmatter(str(tmp_path), updates)
    result = json.loads(result_json)

    assert result["updated_count"] == 1

    # Read the updated file and extract frontmatter key order
    updated_content = tc_file.read_text()
    lines = updated_content.split('\n')
    frontmatter_keys = []
    in_frontmatter = False

    for line in lines:
        if line.strip() == '---':
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter and ':' in line:
            key = line.split(':')[0].strip()
            frontmatter_keys.append(key)

    assert frontmatter_keys[0] == "test_case_id", \
        f"First field should be 'test_case_id', got '{frontmatter_keys[0]}'. " \
        f"Full order: {frontmatter_keys}"


def test_updates_automation_status(tmp_path):
    """Should update automation_status and related fields."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    # Create TC with all required fields for validation
    tc_content = """---
test_case_id: TC-API-001
source_key: RHAISTRAT-1519
priority: P0
status: Draft
last_updated: "2026-05-05"
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
    (tc_dir / "TC-API-001.md").write_text(tc_content)

    updates = [
        {
            "tc_id": "TC-API-001",
            "automation_status": "Complete",
            "automation_file": "tests/test_api.py",
            "automation_function": "test_create_notebook"
        }
    ]

    result = update_tc_frontmatter(str(tmp_path), updates)
    data = json.loads(result)

    assert data['updated_count'] == 1
    assert "TC-API-001" in data['updated_tcs']

    # Verify file was actually updated
    fm, _ = read_frontmatter(str(tc_dir / "TC-API-001.md"))
    assert fm['automation_status'] == 'Complete'
    assert fm['automation_file'] == 'tests/test_api.py'
    assert fm['automation_function'] == 'test_create_notebook'


def test_handles_missing_tc_file(tmp_path):
    """Should report error for missing TC file."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    updates = [{"tc_id": "TC-MISSING-001", "automation_status": "Complete"}]

    result = update_tc_frontmatter(str(tmp_path), updates)
    data = json.loads(result)

    assert data['updated_count'] == 0
    assert len(data['errors']) == 1
    assert "TC-MISSING-001" in data['errors'][0]
