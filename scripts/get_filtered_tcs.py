#!/usr/bin/env python3
"""
Extract specific field from .test_cases_filter.json, creating it if needed.

Single entry point for test case filtering in skills. Handles:
- Auto-discovery of TCs if none provided
- Filtering by automation_status and UI category
- Interactive confirmation for re-implementing (auto-determined by CLAUDE_NON_INTERACTIVE env var)
- Reading/creating .test_cases_filter.json
- Returning specific field (be_test_cases, ui_test_cases, already_implemented)

Behavior:
- If .test_cases_filter.json exists: reads and returns field
- If missing: runs filtering, prompts for re-implement (if interactive), writes file, returns field
- Interactive mode (CLAUDE_NON_INTERACTIVE not set): prompts user to re-implement already_implemented TCs
- CI mode (CLAUDE_NON_INTERACTIVE=true): skips prompt, doesn't re-implement

Usage:
    python scripts/get_filtered_tcs.py <feature_dir> <field_name> [tc_id ...]

Examples:
    # Get all backend test cases (auto-discovers if .test_cases_filter.json missing)
    python scripts/get_filtered_tcs.py ~/path/to/feature be_test_cases

    # Get specific backend test cases
    python scripts/get_filtered_tcs.py ~/path/to/feature be_test_cases TC-E2E-001 TC-E2E-002

    # Get UI test cases
    python scripts/get_filtered_tcs.py ~/path/to/feature ui_test_cases

Output:
    Space-separated list of TC IDs: TC-E2E-001 TC-E2E-002 TC-NEG-001
"""

import json
import sys
from pathlib import Path

from scripts.filter_test_cases import filter_and_confirm_test_cases
from scripts.utils.error_utils import exit_error


def get_filtered_tcs(feature_dir: str, field_name: str, tc_ids: list[str] | None = None) -> list[str]:
    """
    Get filtered test cases for a specific field.

    If .test_cases_filter.json doesn't exist, automatically creates it by
    running filter_and_confirm_test_cases() with confirmation behavior
    determined by CLAUDE_NON_INTERACTIVE environment variable.

    Args:
        feature_dir: Path to feature directory
        field_name: Field to extract (be_test_cases, ui_test_cases, already_implemented)
        tc_ids: Optional list of TC IDs to filter (returns intersection with field)

    Returns:
        List of TC IDs

    Raises:
        KeyError: If field_name is not valid
    """
    filter_file = Path(feature_dir) / ".test_cases_filter.json"

    # If filter file doesn't exist, create it (with auto-confirmation based on env)
    if not filter_file.exists():
        # Always pass None to filter ALL TCs - tc_ids is only for final intersection
        filter_and_confirm_test_cases(feature_dir, None, confirm=True)

    data = json.loads(filter_file.read_text())

    valid_fields = ["be_test_cases", "ui_test_cases", "already_implemented"]
    if field_name not in valid_fields:
        raise KeyError(f"Invalid field '{field_name}'. Valid fields: {', '.join(valid_fields)}")

    result = data[field_name]

    # If specific TC IDs provided, return only those that are in the field
    if tc_ids:
        # Strip .md extension if present (handles both TC-NEG-001 and TC-NEG-001.md)
        tc_set = {tc.removesuffix(".md") for tc in tc_ids}
        result = [tc for tc in result if tc in tc_set]

    return result


def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        exit_error("Usage: python scripts/get_filtered_tcs.py <feature_dir> <field_name> [tc_id ...]")

    feature_dir = sys.argv[1]
    field_name = sys.argv[2]
    tc_ids = sys.argv[3:] if len(sys.argv) > 3 else None

    # Handle both comma-separated and space-separated TC IDs
    # Example: "TC-001,TC-002" OR "TC-001 TC-002"
    if tc_ids and len(tc_ids) == 1 and "," in tc_ids[0]:
        tc_ids = tc_ids[0].split(",")

    try:
        result = get_filtered_tcs(feature_dir, field_name, tc_ids)
        # Print space-separated for easy use in bash
        print(" ".join(result))
    except KeyError as e:
        exit_error(f"Error: {e}")
    except Exception as e:
        exit_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
