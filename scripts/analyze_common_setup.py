#!/usr/bin/env python3
"""Identify common setup requirements across test cases."""
import json
import sys
from pathlib import Path

from scripts.utils.test_analyzer import identify_common_setup_requirements
from scripts.parse_test_cases import parse_test_cases


def analyze_common_setup(feature_dir: str) -> str:
    """
    Identify preconditions used by 2+ test cases.

    Args:
        feature_dir: Path to feature directory

    Returns:
        JSON string with common setup requirements
    """
    # Get all TC IDs by scanning test case files directly
    # (INDEX.md is derived from TC files, so files are source of truth)
    tc_dir = Path(feature_dir) / "test_cases"
    if not tc_dir.exists():
        return json.dumps([])

    # Use glob pattern (same as validate_feature_dir, tc_regeneration, etc.)
    tc_ids = [f.stem for f in tc_dir.glob("TC-*.md")]

    if not tc_ids:
        return json.dumps([])

    # Parse all TCs
    test_cases_json = parse_test_cases(feature_dir, tc_ids)
    test_cases = json.loads(test_cases_json)

    # Analyze common setup
    common_requirements = identify_common_setup_requirements(test_cases)

    return json.dumps(common_requirements, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_common_setup.py <feature_dir>",
              file=sys.stderr)
        sys.exit(1)

    try:
        result = analyze_common_setup(sys.argv[1])
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
