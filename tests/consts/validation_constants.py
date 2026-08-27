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
VALID_SCOPE_COVERAGE = {"valid": True, "missing": [], "unmapped_objectives": []}
INVALID_SCOPE_COVERAGE = {
    "valid": False,
    "missing": [
        {
            "section": "2.3",
            "text": "Optional description and tags",
            "reason": "no Section 1.3 objective",
        }
    ],
    "unmapped_objectives": [],
}
INVALID_SCOPE_COVERAGE_REVERSE = {
    "valid": False,
    "missing": [],
    "unmapped_objectives": [
        {
            "section": "1.3",
            "text": "Verify an invented deliverable",
            "reason": "no grounded strategy requirement",
        }
    ],
}
VALID_ACTIONABILITY = {"valid": True, "bare_tbd": [], "missing_details": []}
INVALID_ACTIONABILITY = {
    "valid": False,
    "bare_tbd": ["OpenShift version", "RHOAI version"],
    "missing_details": ["RBAC roles and permissions"],
}
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

# Bytes that are not valid UTF-8 — Path.read_text(encoding="utf-8") raises UnicodeDecodeError.
NON_UTF8_PLAN_BYTES = b"\xff\xfe not utf-8"

# Kinds of unreadable test_plan_path for load_and_detect / load_and_validate wrappers.
UNREADABLE_TEST_PLAN_KINDS = ("directory", "non_utf8")

# Values that must not be accepted as list[str] config fields (string splits into chars;
# null / nested lists TypeError in merge/_dedupe). Loaders must raise ValueError instead.
INVALID_LIST_STR_FIELD_VALUES = ("a string", None, [["nested"]])
INVALID_LIST_STR_FIELD_IDS = ("string", "null", "nested-list")
SCOPE_LIST_FIELDS = ("allowed_test_levels", "forbidden_test_levels", "forbidden_patterns")
BOILERPLATE_PATTERN_CATEGORIES = ("objectives", "risks", "priorities")

# Structured evidence fixtures for validate_quality_evidence.py. Scope-bearing plan entries
# must explicitly identify the Section 1.3 objective they implement with `(Objective: #N)`.
# The objective, in turn, cites the STRAT requirement using the existing `(AC: #N — ...)` or
# `(NFR: category — ...)` syntax. This validates a concrete mapping chain without trying to
# infer semantic similarity from free-form prose.
QUALITY_EVIDENCE_STRATEGY = "h3. Acceptance Criteria\n\n# Given a user registers a store, then it persists\n"
QUALITY_EVIDENCE_OBJECTIVE = "1. Verify store registration (AC: #1 — registration persists)"
QUALITY_EVIDENCE_OBJECTIVES_SECTION = f"{TEMPLATE_HEADINGS['1.3']}\n\n{QUALITY_EVIDENCE_OBJECTIVE}"

UNMAPPED_SCOPE_CASES = (
    (
        "1.2",
        f"{TEMPLATE_HEADINGS['1.2']}\n\n- Register a store through the API",
        "Register a store through the API",
    ),
    (
        "2.3",
        f"{TEMPLATE_HEADINGS['2.3']}\n\n- **P0 (Critical)** — register a store",
        "**P0 (Critical)** — register a store",
    ),
    (
        "7.1",
        f"{TEMPLATE_HEADINGS['7.1']}\n\n- Verify mirrored images are available to the registration service",
        "Verify mirrored images are available to the registration service",
    ),
    (
        "7.2",
        f"{TEMPLATE_HEADINGS['7.2']}\n\n- Verify store registrations survive the operator upgrade",
        "Verify store registrations survive the operator upgrade",
    ),
    (
        "7.3",
        f"{TEMPLATE_HEADINGS['7.3']}\n\n- Verify concurrent store registrations remain within the latency target",
        "Verify concurrent store registrations remain within the latency target",
    ),
    (
        "7.4",
        f"{TEMPLATE_HEADINGS['7.4']}\n\n- Verify service-account authorization for store registration",
        "Verify service-account authorization for store registration",
    ),
    (
        "7.5",
        f"{TEMPLATE_HEADINGS['7.5']}\n\n- Verify registration requests require valid service credentials",
        "Verify registration requests require valid service credentials",
    ),
    (
        "8",
        f"{TEMPLATE_HEADINGS['8']}\n\n"
        "| Risk | Impact | Probability | Mitigation |\n"
        "|------|--------|-------------|------------|\n"
        "| Store registration is unavailable | High | Medium | Retry the API request |",
        "Store registration is unavailable",
    ),
)

FULLY_MAPPED_SCOPE_PLAN = f"""{TEMPLATE_HEADINGS["1.2"]}

- Register a store through the API (Objective: #1)

{QUALITY_EVIDENCE_OBJECTIVES_SECTION}

{TEMPLATE_HEADINGS["2.3"]}

- **P0 (Critical)** — register a store (Objective: #1)

{TEMPLATE_HEADINGS["7.4"]}

- Verify service-account authorization for store registration (Objective: #1)

{TEMPLATE_HEADINGS["8"]}

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Store registration is unavailable | High | Medium | Retry the API request (Objective: #1) |
"""

# NFR category with no concrete grounding — a bare "Not Applicable" statement must not need
# `(Objective: #N)`, since no Section 1.3 objective was ever created for it.
NOT_APPLICABLE_NFR_SECTIONS = ("7.1", "7.2", "7.3", "7.4", "7.5")
NOT_APPLICABLE_NFR_CASES = tuple(
    (
        section,
        f"{QUALITY_EVIDENCE_OBJECTIVES_SECTION}\n\n"
        f"{TEMPLATE_HEADINGS[section]}\n\n"
        "**Not Applicable** — this feature has no grounding for this category.\n",
    )
    for section in NOT_APPLICABLE_NFR_SECTIONS
)

ACTIONABILITY_CONCRETE_DATA_AND_RBAC = f"""{TEMPLATE_HEADINGS["3.2"]}

| Format | Example |
|--------|---------|
| JSON object with a unique name | {{"name": "orders"}} |

{TEMPLATE_HEADINGS["3.3"]}

| Role | Resource | Permissions |
|------|----------|-------------|
| QE administrator | vector-store resources | create, get, delete |
"""

ACTIONABILITY_TBD_UNKNOWN_PLAN = f"""{TEMPLATE_HEADINGS["3.1"]}

OpenShift version: TBD — unknown
RHOAI version: 2.25

{ACTIONABILITY_CONCRETE_DATA_AND_RBAC}
"""

ACTIONABILITY_TBD_DATA_PLAN = f"""{TEMPLATE_HEADINGS["3.1"]}

OpenShift version: 4.18
RHOAI version: 2.25

{TEMPLATE_HEADINGS["3.2"]}

Payload format: TBD; Example: TBD

{TEMPLATE_HEADINGS["3.3"]}

| Role | Resource | Permissions |
|------|----------|-------------|
| QE administrator | vector-store resources | create, get, delete |
"""

ACTIONABILITY_PROSE_RBAC_PLAN = f"""{TEMPLATE_HEADINGS["3.1"]}

OpenShift version: 4.18
RHOAI version: 2.25

{TEMPLATE_HEADINGS["3.2"]}

| Format | Example |
|--------|---------|
| JSON object with a unique name | {{"name": "orders"}} |

{TEMPLATE_HEADINGS["3.3"]}

The test user role has permissions and can access the environment.
"""

ACTIONABILITY_GENERIC_PROSE_RBAC_PLAN = f"""{TEMPLATE_HEADINGS["3.1"]}

OpenShift version: 4.18
RHOAI version: 2.25

{TEMPLATE_HEADINGS["3.2"]}

| Format | Example |
|--------|---------|
| JSON object with a unique name | {{"name": "orders"}} |

{TEMPLATE_HEADINGS["3.3"]}

The test user can create, get, and delete all resources.
"""

ACTIONABILITY_CONCRETE_PROSE_RBAC_PLAN = f"""{TEMPLATE_HEADINGS["3.1"]}

OpenShift version: 4.18
RHOAI version: 2.25

{TEMPLATE_HEADINGS["3.2"]}

| Format | Example |
|--------|---------|
| JSON object with a unique name | {{"name": "orders"}} |

{TEMPLATE_HEADINGS["3.3"]}

The qe-test-user can create, get, and delete vector-store resources.
"""

ACTIONABILITY_RBAC_WITHOUT_RESOURCE_PLAN = f"""{TEMPLATE_HEADINGS["3.1"]}

OpenShift version: 4.18
RHOAI version: 2.25

{TEMPLATE_HEADINGS["3.2"]}

Registration payload: JSON object; Example: {{"name": "orders"}}

{TEMPLATE_HEADINGS["3.3"]}

| Role | Permissions |
|------|-------------|
| QE administrator | create, get, delete |
"""

ACTIONABILITY_DELIMITED_DATA_PLACEHOLDER_PLAN = f"""{TEMPLATE_HEADINGS["3.1"]}

OpenShift version: 4.18
RHOAI version: 2.25

{TEMPLATE_HEADINGS["3.2"]}

Registration payload: JSON object; Example: {{placeholder}}

{TEMPLATE_HEADINGS["3.3"]}

| Role | Resource | Permissions |
|------|----------|-------------|
| QE administrator | vector-store resources | create, get, delete |
"""

ACTIONABILITY_JUSTIFIED_TBD_PLAN = f"""{TEMPLATE_HEADINGS["3.1"]}

OpenShift version: TBD — Resolution: retrieve the supported-platform matrix from platform engineering before setup.
RHOAI version: 2.25

{ACTIONABILITY_CONCRETE_DATA_AND_RBAC}
"""
