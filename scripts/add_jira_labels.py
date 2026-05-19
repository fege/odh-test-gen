#!/usr/bin/env python3
"""
Add labels to a Jira issue.

This script wraps jira_utils.add_labels() for use in skills,
avoiding fragile shell string manipulation.

Usage:
    # Add single label
    python scripts/add_jira_labels.py RHAISTRAT-400 test-plan-auto-created

    # Add multiple labels
    python scripts/add_jira_labels.py RHAISTRAT-400 test-plan-rubric-pass test-plan-auto-revised

Environment variables:
    JIRA_URL   - Jira server URL (required)
    JIRA_USER  - Jira username/email (required)
    JIRA_TOKEN - Jira API token (required)

Exit codes:
    0 - Success
    1 - Error (missing args, API failure, missing credentials)
"""

import argparse
import sys
from scripts.jira_utils import add_labels


def main():
    parser = argparse.ArgumentParser(
        description="Add labels to a Jira issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s RHAISTRAT-400 test-plan-auto-created
  %(prog)s RHOAIENG-123 label-one label-two label-three
        """
    )
    parser.add_argument(
        "issue_key",
        help="Jira issue key (e.g., RHAISTRAT-400, RHOAIENG-123)"
    )
    parser.add_argument(
        "labels",
        nargs="+",
        help="One or more labels to add"
    )

    args = parser.parse_args()

    try:
        add_labels(args.issue_key, args.labels)
        print(f"✓ Added {len(args.labels)} label(s) to {args.issue_key}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
