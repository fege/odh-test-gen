"""Pure utility functions for test-plan.ui-verify.

Extracted here so they can be unit-tested independently of the
scripts that use subprocess calls and external connections.
"""

# Keywords that indicate a TC step exercises the browser UI.
UI_KEYWORDS = [
    "navigate", "click", "filter", "catalog", "dashboard", "UI", "page",
    "model card", "sidebar", "browser", "display", "render", "visible",
    "button", "checkbox", "tag", "label", "search", "scroll",
]


def is_ui_test(steps: list) -> bool:
    """Return True if any TC step contains a UI interaction keyword."""
    text = " ".join(steps).lower()
    return any(kw.lower() in text for kw in UI_KEYWORDS)


def matches_tc_filter(tc_id: str, patterns: list) -> bool:
    """Return True if tc_id matches any filter pattern.

    Supports:
    - Exact match:      TC-FILTER-001 matches TC-FILTER-001
    - Category prefix:  TC-FILTER    matches TC-FILTER-001, TC-FILTER-002, …
    """
    if not patterns:
        return True
    return any(tc_id == p or tc_id.startswith(p + "-") for p in patterns)
