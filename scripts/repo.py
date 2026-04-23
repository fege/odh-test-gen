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

    # Locate feature directory from various source types
    uv run python scripts/repo.py locate-feature-dir <source>
    # Outputs JSON: {"feature_dir": "/path", "source_type": "local|github", "repo_owner": "...", "repo_name": "..."}
    # Exit code: 0 if success, 1 if failed

Examples:
    uv run python scripts/repo.py find collection-tests
    uv run python scripts/repo.py find-known odh-test-context
    uv run python scripts/repo.py find-target opendatahub-io/odh-dashboard
    uv run python scripts/repo.py clone https://github.com/fege/test-plan ~/Code/test-plan
    uv run python scripts/repo.py locate-feature-dir ~/Code/collection-tests/mcp_catalog
    uv run python scripts/repo.py locate-feature-dir https://github.com/org/repo/pull/5
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

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


def cmd_locate_feature_dir(args):
    """Locate test plan feature directory from various source types."""
    source = args.source

    # GitHub PR URL: https://github.com/owner/repo/pull/123
    pr_match = re.match(r'^https://github.com/([^/]+)/([^/]+)/pull/(\d+)$', source)
    if pr_match:
        owner, repo, pr_number = pr_match.groups()
        return _handle_github_pr(owner, repo, pr_number)

    # GitHub branch URL: https://github.com/owner/repo/tree/branch-name
    branch_match = re.match(r'^https://github.com/([^/]+)/([^/]+)/tree/(.+)$', source)
    if branch_match:
        owner, repo, branch = branch_match.groups()
        return _handle_github_branch(owner, repo, branch)

    # Local directory path
    return _handle_local_path(source)


def _handle_github_pr(owner, repo, pr_number):
    """Handle GitHub PR URL - fetch branch name and process."""
    try:
        # Fetch PR metadata to get branch name
        result = subprocess.run(
            ["gh", "pr", "view", pr_number, "--repo", f"{owner}/{repo}", "--json", "headRefName"],
            capture_output=True,
            text=True,
            check=True
        )
        pr_data = json.loads(result.stdout)
        branch_name = pr_data["headRefName"]

        return _handle_github_branch(owner, repo, branch_name)
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"ERROR: Failed to fetch PR {pr_number}: {e}", file=sys.stderr)
        return 1


def _handle_github_branch(owner, repo, branch):
    """Handle GitHub branch - find/clone repo, checkout branch, find TestPlan.md."""
    # Check if repo exists locally
    repo_path = find_repo_in_common_locations(repo)

    if repo_path:
        # Repo found locally - checkout branch
        try:
            subprocess.run(["git", "fetch", "origin"], cwd=repo_path, check=True, capture_output=True)
            # Try to checkout existing branch or create tracking branch
            checkout_result = subprocess.run(
                ["git", "checkout", branch],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if checkout_result.returncode != 0:
                # Branch doesn't exist locally, create tracking branch
                subprocess.run(
                    ["git", "checkout", "-b", branch, f"origin/{branch}"],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )
            subprocess.run(["git", "pull", "origin", branch], cwd=repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Git operations failed: {e}", file=sys.stderr)
            return 1
    else:
        # Clone repo
        repo_url = f"https://github.com/{owner}/{repo}.git"
        target_path = os.path.expanduser(f"~/Code/{repo}")
        repo_path = clone_repo(repo_url, target_path)
        if not repo_path:
            print(f"ERROR: Failed to clone {repo_url}", file=sys.stderr)
            return 1

        # Checkout branch
        try:
            subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Failed to checkout branch {branch}: {e}", file=sys.stderr)
            return 1

    # Find TestPlan.md in the repository
    feature_dir = _find_testplan_in_repo(repo_path)
    if not feature_dir:
        print(f"ERROR: TestPlan.md not found in {repo_path}", file=sys.stderr)
        return 1

    # Output results
    result = {
        "feature_dir": feature_dir,
        "source_type": "github",
        "repo_owner": owner,
        "repo_name": repo
    }
    print(json.dumps(result, indent=2))
    return 0


def _handle_local_path(path):
    """Handle local directory path - validate and return."""
    # Expand ~ to home directory
    path = os.path.expanduser(path)

    # Convert to absolute path
    if not os.path.isabs(path):
        path = os.path.abspath(path)

    # Verify TestPlan.md exists
    testplan_path = os.path.join(path, "TestPlan.md")
    if not os.path.isfile(testplan_path):
        print(f"ERROR: TestPlan.md not found at {path}", file=sys.stderr)
        return 1

    # Output results
    result = {
        "feature_dir": path,
        "source_type": "local"
    }
    print(json.dumps(result, indent=2))
    return 0


def _find_testplan_in_repo(repo_path):
    """Find TestPlan.md in repository (may be in subdirectory)."""
    repo_path = Path(repo_path)

    # Search for TestPlan.md
    for testplan in repo_path.rglob("TestPlan.md"):
        # Return the directory containing TestPlan.md
        return str(testplan.parent)

    return None


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

    # locate-feature-dir command
    parser_locate = subparsers.add_parser(
        "locate-feature-dir",
        help="Locate test plan feature directory from local path or GitHub URL"
    )
    parser_locate.add_argument(
        "source",
        help="Local path, GitHub PR URL, or GitHub branch URL"
    )
    parser_locate.set_defaults(func=cmd_locate_feature_dir)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
