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
from scripts.utils.error_utils import exit_error_with_json


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

    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code != 0:
            exit_error_with_json(json_output={"status": "failed", "error": "invalid_arguments"})
        sys.exit(0)

    labels = list(args.labels)
    stale_rubric_labels = []

    if args.verdict is not None:
        verdict_label = rubric_label_for_verdict(args.verdict)
        if verdict_label is None:
            # Skills always pass --verdict "$verdict"; unrecognized values must skip the
            # rubric stamp without blocking literal labels (e.g. test-plan-auto-revised).
            print(
                f"Warning: Unexpected verdict '{args.verdict}', skipping rubric label",
                file=sys.stderr,
            )
        else:
            # Literal rubric labels must not disagree with --verdict; otherwise
            # add_labels would persist both and leave conflicting rubric state.
            conflicting = (set(labels) & set(RUBRIC_LABELS.values())) - {verdict_label}
            if conflicting:
                print(
                    f"Error: literal rubric label(s) {sorted(conflicting)} conflict with "
                    f"--verdict {args.verdict} ({verdict_label})",
                    file=sys.stderr,
                )
                print(json.dumps({"status": "error", "error": "conflicting_rubric_labels"}))
                return 1

            labels.insert(0, verdict_label)
            # Rubric labels are mutually exclusive: a verdict change must replace the
            # previous one, not accumulate alongside it (add_labels only ever appends).
            stale_rubric_labels = [label for label in RUBRIC_LABELS.values() if label != verdict_label]

    if not labels:
        if args.verdict is not None and rubric_label_for_verdict(args.verdict) is None:
            print(f"Error: invalid verdict '{args.verdict}' and no other labels to add", file=sys.stderr)
            print(json.dumps({"status": "error", "error": "invalid_verdict"}))
            return 1
        else:
            print("Error: No labels to add (no --verdict match and no literal labels given)", file=sys.stderr)
            print(json.dumps({"status": "error", "error": "no_labels_to_add"}))
            return 1

    try:
        add_labels(args.issue_key, labels, remove=stale_rubric_labels)
        print(f"✓ Added {len(labels)} label(s) to {args.issue_key}", file=sys.stderr)
        return 0
    except Exception:
        print("Error: Failed to add labels to Jira issue", file=sys.stderr)
        print(json.dumps({"status": "error", "error": "add_labels_failed"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
