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
import json
import sys

from scripts.jira_utils import add_labels


RUBRIC_LABELS = {
    "Ready": "test-plan-rubric-pass",
    "Revise": "test-plan-rubric-revise",
    "Rework": "test-plan-rubric-fail",
}


def rubric_label_for_verdict(verdict):
    """Return the Jira rubric label for a review verdict, or None if unrecognized."""
    return RUBRIC_LABELS.get(verdict)


def main():
    parser = argparse.ArgumentParser(
        description="Add labels to a Jira issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s RHAISTRAT-400 test-plan-auto-created
  %(prog)s RHOAIENG-123 label-one label-two label-three
  %(prog)s RHAISTRAT-400 --verdict Ready test-plan-auto-revised
        """,
    )
    parser.add_argument("issue_key", help="Jira issue key (e.g., RHAISTRAT-400, RHOAIENG-123)")
    parser.add_argument("--verdict", help="Review verdict (Ready, Revise, or Rework)")
    parser.add_argument("labels", nargs="*", help="One or more labels to add")

    args = parser.parse_args()

    labels = list(args.labels)
    stale_rubric_labels = []

    if args.verdict:
        if verdict_label := rubric_label_for_verdict(args.verdict):
            labels.insert(0, verdict_label)
            # Rubric labels are mutually exclusive: a verdict change must replace the
            # previous one, not accumulate alongside it (add_labels only ever appends).
            stale_rubric_labels = [label for label in RUBRIC_LABELS.values() if label != verdict_label]
        else:
            print(f"Warning: Unexpected verdict '{args.verdict}', skipping rubric label", file=sys.stderr)

    if not labels:
        message = "No labels to add (no --verdict match and no literal labels given)"
        print(f"Error: {message}", file=sys.stderr)
        print(json.dumps({"status": "error", "error": message}))
        return 1

    try:
        add_labels(args.issue_key, labels, remove=stale_rubric_labels)
        print(f"✓ Added {len(labels)} label(s) to {args.issue_key}", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print(json.dumps({"status": "error", "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
