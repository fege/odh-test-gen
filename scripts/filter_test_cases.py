#!/usr/bin/env python3
"""
Filter test cases by automation status.

Separates test cases into 'to_implement' and 'already_implemented'
based on the automation_status field in TC frontmatter.

Usage:
    python scripts/filter_test_cases.py <feature_dir> <tc_id_1> <tc_id_2> ...

Output (JSON):
    {
        "to_implement": ["TC-API-002", "TC-API-003"],
        "already_implemented": ["TC-API-001"]
    }
"""

import json
import sys
from pathlib import Path
from typing import List

from scripts.utils.frontmatter_utils import read_frontmatter


def filter_test_cases(feature_dir: str, tc_ids: List[str]) -> str:
    """
    Filter test cases by automation status.

    Args:
        feature_dir: Path to feature directory
        tc_ids: List of test case IDs to filter

    Returns:
        JSON string with filtering results

    Raises:
        FileNotFoundError: If any TC file is missing
    """
    feature_path = Path(feature_dir)
    tc_dir = feature_path / "test_cases"

    to_implement = []
    already_implemented = []

    for tc_id in tc_ids:
        tc_file = tc_dir / f"{tc_id}.md"

        if not tc_file.exists():
            raise FileNotFoundError(f"{tc_id}.md not found at {tc_file}")

        # Read frontmatter
        frontmatter, _ = read_frontmatter(str(tc_file))

        # Check automation_status
        automation_status = frontmatter.get('automation_status', '').strip().lower()

        # Consider 'implemented' as already done
        if automation_status == 'implemented':
            already_implemented.append(tc_id)
        else:
            # All other statuses (Not Started, In Progress, null, etc.) need implementation
            to_implement.append(tc_id)

    return json.dumps({
        'to_implement': to_implement,
        'already_implemented': already_implemented,
    }, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/filter_test_cases.py <feature_dir> [tc_id ...]",
              file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]
    tc_ids = sys.argv[2:]  # Can be empty

    try:
        result = filter_test_cases(feature_dir, tc_ids)
        print(result)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
