#!/usr/bin/env python3
"""CLI for repository discovery and management utilities.

Skills call this script to find repositories, clone them, and load test context.

Usage:
    # Find a repository in common locations
    uv run python scripts/repo.py find <repo_name>
    # Outputs: /absolute/path/to/repo (or empty if not found)
    # Exit code: 0 if found, 1 if not found

    # Find a known repository (odh-test-context, tiger-team)
    uv run python scripts/repo.py find-known <repo_type>
    # Outputs JSON: {"path": "/path/to/repo", "url": "https://..."}
    # Exit code: 0 if found, 1 if not found

    # Find a target repository (handles org/repo format)
    uv run python scripts/repo.py find-target <repo_name>
    # Outputs: /absolute/path/to/repo (or empty if not found)
    # Exit code: 0 if found, 1 if not found

    # Clone a repository
    uv run python scripts/repo.py clone <repo_url> <target_path>
    # Outputs: /absolute/path/to/cloned/repo
    # Exit code: 0 if success, 1 if failed

Examples:
    uv run python scripts/repo.py find collection-tests
    uv run python scripts/repo.py find-known odh-test-context
    uv run python scripts/repo.py find-target opendatahub-io/odh-dashboard
    uv run python scripts/repo.py clone https://github.com/fege/test-plan ~/Code/test-plan
"""

import argparse
import json
import sys

from scripts.utils.repo_utils import (
    find_repo_in_common_locations,
    find_known_repo,
    find_target_repo,
    clone_repo,
)


def cmd_find(args):
    """Find repository in common locations."""
    result = find_repo_in_common_locations(args.repo_name)
    if result:
        print(result)
        return 0
    else:
        return 1


def cmd_find_known(args):
    """Find known repository (odh-test-context, tiger-team)."""
    try:
        path, url = find_known_repo(args.repo_type)
        result = {"path": path, "url": url}
        print(json.dumps(result, indent=2))
        return 0 if path else 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_find_target(args):
    """Find target repository (handles org/repo format)."""
    result = find_target_repo(args.repo_name)
    if result:
        print(result)
        return 0
    else:
        return 1


def cmd_clone(args):
    """Clone repository."""
    result = clone_repo(args.repo_url, args.target_path)
    if result:
        print(result)
        return 0
    else:
        print(f"Failed to clone {args.repo_url}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Repository discovery and management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # find command
    parser_find = subparsers.add_parser(
        "find",
        help="Find repository in common locations"
    )
    parser_find.add_argument("repo_name", help="Repository name to find")
    parser_find.set_defaults(func=cmd_find)

    # find-known command
    parser_find_known = subparsers.add_parser(
        "find-known",
        help="Find known repository (odh-test-context, tiger-team)"
    )
    parser_find_known.add_argument(
        "repo_type",
        choices=["odh-test-context", "tiger-team"],
        help="Type of known repository"
    )
    parser_find_known.set_defaults(func=cmd_find_known)

    # find-target command
    parser_find_target = subparsers.add_parser(
        "find-target",
        help="Find target repository (handles org/repo format)"
    )
    parser_find_target.add_argument(
        "repo_name",
        help="Repository name (with or without org)"
    )
    parser_find_target.set_defaults(func=cmd_find_target)

    # clone command
    parser_clone = subparsers.add_parser(
        "clone",
        help="Clone repository"
    )
    parser_clone.add_argument("repo_url", help="GitHub URL to clone")
    parser_clone.add_argument("target_path", help="Where to clone (~ expanded)")
    parser_clone.set_defaults(func=cmd_clone)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
