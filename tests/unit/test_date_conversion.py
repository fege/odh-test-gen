"""
Unit tests for date object to string conversion in schemas.

Tests that YAML date objects are automatically converted to strings.
"""

import datetime

from scripts.utils.schemas import validate


def test_converts_date_object_to_string():
    """Should convert Python date object to string for validation."""
    data = {
        "test_case_id": "TC-API-001",
        "priority": "P0",
        "source_key": "RHAISTRAT-400",
        "status": "Draft",
        "last_updated": datetime.date(2026, 5, 4),  # Date object, not string
    }

    errors = validate(data, "test-case")

    # Should not have error about last_updated being a date
    assert not any("last_updated" in e and "expected string" in e for e in errors)


def test_accepts_string_dates():
    """Should still accept string dates."""
    data = {
        "test_case_id": "TC-API-001",
        "priority": "P0",
        "source_key": "RHAISTRAT-400",
        "status": "Draft",
        "last_updated": "2026-05-04",  # String
    }

    errors = validate(data, "test-case")

    assert not any("last_updated" in e for e in errors)
