#!/usr/bin/env python3
"""
Update test case frontmatter fields in bulk.

Updates automation_status, automation_file, and automation_function fields for implemented test cases.

Usage:
    python scripts/update_tc_frontmatter.py <feature_dir> <updates.json>

updates.json format:
    [
        {
            "tc_id": "TC-API-001",
            "automation_status": "Complete",
            "automation_file": "tests/test_api.py",
            "automation_function": "test_create_notebook"
        }
    ]

Output (JSON):
    {
        "updated_count": 2,
        "updated_tcs": ["TC-API-001", "TC-API-002"],
        "errors": []
    }
"""

import json
import sys
from pathlib import Path
from typing import List, Dict

from scripts.utils.frontmatter_utils import update_frontmatter


def update_tc_frontmatter(feature_dir: str, updates: List[Dict]) -> str:
    """
    Update TC frontmatter fields in bulk.

    Args:
        feature_dir: Path to feature directory
        updates: List of update dicts with tc_id and fields to update

    Returns:
        JSON string with update results
    """
    feature_path = Path(feature_dir)
    tc_dir = feature_path / "test_cases"

    updated_tcs = []
    errors = []

    for update in updates:
        tc_id = update['tc_id']
        tc_file = tc_dir / f"{tc_id}.md"

        if not tc_file.exists():
            errors.append(f"{tc_id}: File not found at {tc_file}")
            continue

        try:
            # Prepare updates (exclude tc_id)
            field_updates = {k: v for k, v in update.items() if k != 'tc_id'}

            # Use shared utility (validates against test-case schema and formats consistently)
            update_frontmatter(str(tc_file), field_updates, "test-case")

            updated_tcs.append(tc_id)

        except Exception as e:
            errors.append(f"{tc_id}: {str(e)}")

    return json.dumps({
        'updated_count': len(updated_tcs),
        'updated_tcs': updated_tcs,
        'errors': errors,
    }, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) != 3:
        print("Usage: python scripts/update_tc_frontmatter.py <feature_dir> <updates.json>",
              file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]
    updates_file = sys.argv[2]

    try:
        # Read updates from file or stdin
        if updates_file == '-':
            updates = json.load(sys.stdin)
        else:
            with open(updates_file, 'r') as f:
                updates = json.load(f)

        result = update_tc_frontmatter(feature_dir, updates)
        print(result)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
