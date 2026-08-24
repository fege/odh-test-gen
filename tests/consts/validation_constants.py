"""Constants for validation pattern tests"""

from scripts.utils.schemas import TEMPLATE_HEADINGS
from scripts.utils.validation_config_loader import load_boilerplate_patterns, load_scope_patterns

# Load actual production configs (single source of truth)
CORE_SCOPE_PATTERNS = load_scope_patterns("scripts/checks", teams=None)
CORE_BOILERPLATE_PATTERNS = load_boilerplate_patterns("scripts/checks", teams=None)

# TestPlan.md with boilerplate in multiple sections (invalid)
TESTPLAN_WITH_BOILERPLATE = f"""---
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

1. Verify the registration works as expected
2. Verify error handling works correctly
3. Test core functionality of the API

{TEMPLATE_HEADINGS["2"]}

{TEMPLATE_HEADINGS["2.1"]}

- **E2E System Testing** — end-to-end workflows

{TEMPLATE_HEADINGS["2.3"]}

- **P0 (Critical)** — core functionality, basic workflow

{TEMPLATE_HEADINGS["8"]}

**Risk**: Dependency on external services

**Mitigation**: Monitor service health

**Risk**: Environment instability

**Mitigation**: Improve infrastructure
"""

VALID_CITATIONS = {"valid": True, "total": 5, "cited": 5, "uncited": [], "invalid_citations": []}
VALID_COVERAGE = {"valid": True, "ac_count": 5, "covered": [1, 2, 3, 4, 5], "missing": []}
INVALID_CITATIONS = {
    "valid": False,
    "total": 2,
    "cited": 0,
    "uncited": [{"text": "1. Verify login (AC: Given a user logs in...)", "line_number": 79}],
    "invalid_citations": [
        {"text": "2. Verify logout (AC: #9 — out of range)", "line_number": 82, "reasons": ["out_of_range"]}
    ],
}
INVALID_COVERAGE = {"valid": False, "ac_count": 5, "covered": [1], "missing": [2, 3, 4, 5]}

VALID_SCOPE_CHECK = {"valid": True, "violations": []}
INVALID_SCOPE_CHECK = {
    "valid": False,
    "violations": [
        {
            "file": "TestPlan.md",
            "line": 10,
            "section": "2.1",
            "matched_pattern": "Unit Testing",
            "violation_type": "forbidden_test_level",
            "context": "- **Unit Testing** — component logic",
        }
    ],
}

VALID_BOILERPLATE = {"valid": True, "total_violations": 0, "by_section": {}}
BOILERPLATE_THREE_VIOLATIONS = {
    "valid": False,
    "total_violations": 3,
    "by_section": {
        "1.3": [
            {
                "file": "TestPlan.md",
                "line": 5,
                "matched_pattern": "works as expected",
                "context": "1. Verify it works as expected",
                "category": "objectives",
            }
        ]
    },
}
BOILERPLATE_FIVE_VIOLATIONS = {**BOILERPLATE_THREE_VIOLATIONS, "total_violations": 5}

# TestPlan.md with no boilerplate (valid)
TESTPLAN_NO_BOILERPLATE = f"""---
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

1. Verify vector store registration creates catalog entry (AC: #1 — "registration persists")
2. Verify proper error handling for invalid credentials (AC: #2 — "invalid credentials return 400")

{TEMPLATE_HEADINGS["2"]}

{TEMPLATE_HEADINGS["2.1"]}

- **E2E System Testing** — end-to-end workflows

{TEMPLATE_HEADINGS["2.3"]}

- **P0 (Critical)** — registration and deletion flows

{TEMPLATE_HEADINGS["8"]}

**Risk**: Dependency on external services - PostgreSQL vector database

**Mitigation**: Integration test suite with containerized PostgreSQL
"""
