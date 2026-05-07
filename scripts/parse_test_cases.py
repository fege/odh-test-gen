#!/usr/bin/env python3
"""Parse test case files into structured data."""
import json
import sys
from pathlib import Path

from scripts.utils.tc_parser import parse_tc_file
from scripts.utils.frontmatter_utils import read_frontmatter


def parse_test_cases(feature_dir: str, tc_ids: list[str]) -> str:
    """
    Parse multiple TC files into structured data.

    Args:
        feature_dir: Path to feature directory
        tc_ids: List of test case IDs to parse

    Returns:
        JSON string with array of parsed TC data
    """
    test_cases = []

    for tc_id in tc_ids:
        tc_file = Path(feature_dir) / "test_cases" / f"{tc_id}.md"

        if not tc_file.exists():
            raise FileNotFoundError(f"{tc_id}.md not found at {tc_file}")

        tc_data = parse_tc_file(str(tc_file), read_frontmatter)
        test_cases.append(tc_data)

    return json.dumps(test_cases, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/parse_test_cases.py <feature_dir> <tc_id_1> [tc_id_2 ...]",
              file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]
    tc_ids = sys.argv[2:]

    try:
        result = parse_test_cases(feature_dir, tc_ids)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
