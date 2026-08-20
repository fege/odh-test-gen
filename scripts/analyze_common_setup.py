#!/usr/bin/env python3
"""Identify common setup requirements across test cases."""

import json
import sys
from pathlib import Path

from scripts.utils.error_utils import exit_error
from scripts.parse_test_cases import parse_test_cases
from scripts.utils.test_analyzer import identify_common_setup_requirements


def analyze_common_setup(feature_dir: str, tc_ids: list[str] | None = None) -> str:
    """
    Identify preconditions used by 2+ test cases.

    Args:
        feature_dir: Path to feature directory
        tc_ids: Optional list of TC IDs to analyze (analyzes all if None or empty)

    Returns:
        JSON string with common setup requirements
    """
    tc_dir = Path(feature_dir) / "test_cases"
    if not tc_dir.exists():
        return json.dumps([])

    # None or [] means no filter: analyze all TCs
    if tc_ids is None or len(tc_ids) == 0:
        tc_ids = [f.stem for f in tc_dir.glob("TC-*.md")]

    if not tc_ids:
        return json.dumps([])

    # Parse TCs
    test_cases_json = parse_test_cases(feature_dir, tc_ids)
    test_cases = json.loads(test_cases_json)

    # Analyze common setup
    common_requirements = identify_common_setup_requirements(test_cases)

    return json.dumps(common_requirements, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        exit_error("Usage: python scripts/analyze_common_setup.py <feature_dir> [tc_id ...]")

    feature_dir = sys.argv[1]
    tc_ids = sys.argv[2:] if len(sys.argv) > 2 else None

    try:
        result = analyze_common_setup(feature_dir, tc_ids)
        print(result)
    except Exception as e:
        exit_error(f"Error: {e}")


if __name__ == "__main__":
    main()
