#!/usr/bin/env python3
"""CLI for test case regeneration checks.

Detects existing test cases and prepares for regeneration workflow.

Usage:
    # Check if regeneration is needed
    uv run python scripts/tc_regeneration.py check <feature_dir>
    # Outputs JSON: {"mode": "create|regenerate", "existing_count": N, "files": [...]}
    # Exit code: 0 always (informational only)

Examples:
    uv run python scripts/tc_regeneration.py check ~/Code/opendatahub-test-plans/plans/ai-hub/mcp_catalog
"""

import argparse
import json
import sys
from pathlib import Path


def cmd_check(args):
    """Check if test cases exist and return regeneration metadata."""
    feature_dir = Path(args.feature_dir)
    test_cases_dir = feature_dir / "test_cases"

    # Check if test_cases directory exists
    if not test_cases_dir.exists():
        result = {
            "mode": "create",
            "existing_count": 0,
            "files": []
        }
        print(json.dumps(result, indent=2))
        return 0

    # Find existing TC files
    tc_files = sorted(test_cases_dir.glob("TC-*.md"))

    if not tc_files:
        result = {
            "mode": "create",
            "existing_count": 0,
            "files": []
        }
        print(json.dumps(result, indent=2))
        return 0

    # Regeneration mode - return file list
    result = {
        "mode": "regenerate",
        "existing_count": len(tc_files),
        "files": [str(f) for f in tc_files]
    }
    print(json.dumps(result, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Test case regeneration utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # check command
    parser_check = subparsers.add_parser(
        "check",
        help="Check if test cases exist and determine create vs regenerate mode"
    )
    parser_check.add_argument("feature_dir", help="Feature directory containing test_cases/")
    parser_check.set_defaults(func=cmd_check)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
