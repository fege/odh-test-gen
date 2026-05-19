#!/usr/bin/env python3
"""
Fetch a Jira issue and save it as markdown.

Usage:
    python fetch_issue.py <ISSUE_KEY> [--output <FILE>] [--fields <FIELDS>]

Environment variables:
- JIRA_URL: Base URL for the Jira instance (required)
- JIRA_USER: Username or email for authentication (required)
- JIRA_TOKEN: API token for authentication (required)

Examples:
    python fetch_issue.py RHAISTRAT-400
    python fetch_issue.py RHOAIENG-48676 --output strategy.md
    python fetch_issue.py PROJ-123 --fields summary,description,labels
"""

import argparse
import sys
from typing import Any
from scripts.jira_utils import get_issue


def format_issue_as_markdown(issue_data: dict[str, Any]) -> str:
    """
    Format Jira issue data as markdown.

    Args:
        issue_data: The issue data dictionary from the Jira API

    Returns:
        Formatted markdown string
    """
    fields = issue_data.get("fields", {})

    # Extract key fields
    issue_key = issue_data.get("key", "UNKNOWN")
    summary = fields.get("summary", "No summary")
    description = fields.get("description", "No description provided")
    issue_type = fields.get("issuetype", {}).get("name", "Unknown")
    status = fields.get("status", {}).get("name", "Unknown")
    labels = fields.get("labels", [])
    components = fields.get("components", [])

    # Build markdown
    lines = [
        f"# {issue_key}: {summary}",
        "",
        "## Metadata",
        "",
        f"- **Type**: {issue_type}",
        f"- **Status**: {status}",
    ]

    if labels:
        lines.append(f"- **Labels**: {', '.join(labels)}")

    if components:
        component_names = [c.get("name", "Unknown") for c in components]
        lines.append(f"- **Components**: {', '.join(component_names)}")

    lines.extend([
        "",
        "## Description",
        "",
        description,
        "",
    ])

    return "\n".join(lines)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Fetch a Jira issue and save it as markdown"
    )
    parser.add_argument(
        "issue_key",
        help="The Jira issue key (e.g., RHAISTRAT-400)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--fields",
        help="Comma-separated list of fields to fetch (default: all)"
    )

    args = parser.parse_args()

    try:
        # Fetch the issue
        issue_data = get_issue(args.issue_key, fields=args.fields)

        # Format as markdown
        markdown = format_issue_as_markdown(issue_data)

        # Write to file or stdout
        if args.output:
            with open(args.output, "w") as f:
                f.write(markdown)
            print(f"Issue {args.issue_key} saved to {args.output}", file=sys.stderr)
        else:
            print(markdown)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
