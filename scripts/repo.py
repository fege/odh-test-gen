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

    # Validate local path is not in skill repository (requires CLAUDE_SKILL_DIR env var)
    uv run python scripts/repo.py validate-local-path <path> [--force]
    # Exit code: 0 if valid, 1 if invalid (in skill repo)

    # Validate remote repository is not skill repository (requires CLAUDE_SKILL_DIR env var)
    uv run python scripts/repo.py validate-remote <owner/repo>
    # Exit code: 0 if valid, 1 if invalid (is skill repo)

    # Safely checkout branch with uncommitted changes check and stale branch detection
    uv run python scripts/repo.py safe-checkout <repo_path> <branch> [--remote <remote_name>]
    # Exit code: 0 if success, 1 if uncommitted changes or git error

Examples:
    uv run python scripts/repo.py find opendatahub-test-plans
    uv run python scripts/repo.py find-known odh-test-context
    uv run python scripts/repo.py find-target opendatahub-io/odh-dashboard
    uv run python scripts/repo.py clone https://github.com/opendatahub-io/opendatahub-test-plans ~/Code/opendatahub-test-plans
    uv run python scripts/repo.py locate-feature-dir ~/Code/opendatahub-test-plans/plans/ai-hub/mcp_catalog
    uv run python scripts/repo.py locate-feature-dir https://github.com/org/repo/pull/5
    uv run python scripts/repo.py validate-local-path /tmp/test-validation
    uv run python scripts/repo.py validate-remote opendatahub-io/opendatahub-test-plans
    uv run python scripts/repo.py safe-checkout ~/Code/opendatahub-test-plans test-plan/RHAISTRAT-400
    uv run python scripts/repo.py safe-checkout ~/Code/opendatahub-test-plans test-plan/RHAISTRAT-400 --remote publish-target
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
    get_git_root,
    get_git_remote,
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


def safe_checkout_branch(repo_path, branch, remote="origin"):
    """Safely checkout a branch with safety checks.

    Performs:
    - Uncommitted changes check (fails if dirty)
    - Stale branch detection (warns and updates if behind remote)
    - Creates tracking branch if doesn't exist locally
    - Pulls latest changes

    Args:
        repo_path: Path to git repository
        branch: Branch name to checkout
        remote: Remote name (default: "origin")

    Returns:
        0 on success, 1 on error
    """
    try:
        # Check for dirty working tree
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )

        if status_result.stdout.strip():
            # Uncommitted changes found
            print(f"ERROR: Cannot checkout branch - uncommitted changes in {repo_path}", file=sys.stderr)
            print("Please commit or stash your changes first:", file=sys.stderr)
            print("  git stash", file=sys.stderr)
            print("  # or", file=sys.stderr)
            print("  git add . && git commit -m 'WIP'", file=sys.stderr)
            return 1

        # Fetch latest from remote
        subprocess.run(["git", "fetch", remote], cwd=repo_path, check=True, capture_output=True)

        # Check if branch exists locally
        local_branch_exists = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=repo_path,
            capture_output=True
        ).returncode == 0

        if local_branch_exists:
            # Check if local branch is stale (behind remote)
            local_sha = subprocess.run(
                ["git", "rev-parse", branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            remote_sha = subprocess.run(
                ["git", "rev-parse", f"{remote}/{branch}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            if local_sha != remote_sha:
                print(f"⚠️  Local branch '{branch}' is stale. Updating...", file=sys.stderr)

            # Checkout and pull
            subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "pull", remote, branch], cwd=repo_path, check=True, capture_output=True)
        else:
            # Branch doesn't exist locally, create tracking branch
            subprocess.run(
                ["git", "checkout", "-b", branch, f"{remote}/{branch}"],
                cwd=repo_path,
                check=True,
                capture_output=True
            )

        return 0

    except subprocess.CalledProcessError as e:
        print(f"ERROR: Git operations failed: {e}", file=sys.stderr)
        return 1


def _handle_github_branch(owner, repo, branch):
    """Handle GitHub branch - find/clone repo, checkout branch safely, find TestPlan.md.

    Safety: Checks for uncommitted changes before checkout to prevent data loss.
    """
    repo_path = find_repo_in_common_locations(repo)

    if repo_path:
        # Repo exists locally - use safe checkout
        if safe_checkout_branch(repo_path, branch, remote="origin") != 0:
            return 1
    else:
        # Clone repo to ~/Code
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

    # Find TestPlan.md in the repository (pass branch for disambiguation)
    feature_dir = _find_testplan_in_repo(repo_path, branch_hint=branch)
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


def _find_testplan_in_repo(repo_path, branch_hint=None):
    """Find TestPlan.md in repository (may be in subdirectory).

    Args:
        repo_path: Path to repository
        branch_hint: Optional branch name to help disambiguate (e.g., "test-plan/RHAISTRAT-1507")

    Returns the directory containing TestPlan.md, or None if not found.
    If multiple TestPlan.md exist, uses branch_hint to match source_key in frontmatter.
    """
    repo_path = Path(repo_path)

    # Search for all TestPlan.md files
    testplans = list(repo_path.rglob("TestPlan.md"))

    if not testplans:
        return None

    if len(testplans) == 1:
        # Only one found, no ambiguity
        return str(testplans[0].parent)

    # Multiple TestPlan.md files - try to disambiguate using branch_hint
    if branch_hint:
        # Extract issue key from branch name (e.g., "RHAISTRAT-1507" from "test-plan/RHAISTRAT-1507")
        issue_key_match = re.search(r'(RHAISTRAT|RHOAIENG|RHODA)-\d+', branch_hint)
        if issue_key_match:
            issue_key = issue_key_match.group(0)

            # Search for TestPlan.md with matching source_key in frontmatter
            for testplan in testplans:
                try:
                    content = testplan.read_text()
                    # Quick check for source_key in frontmatter
                    if f'source_key: {issue_key}' in content[:500]:
                        return str(testplan.parent)
                except Exception:
                    continue

    # Multiple features found and couldn't disambiguate
    relative_paths = [str(t.relative_to(repo_path)) for t in testplans]
    print(f"ERROR: Multiple TestPlan.md files found in {repo_path}:", file=sys.stderr)
    for path in sorted(relative_paths):
        print(f"  - {path}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Please specify the feature directory explicitly:", file=sys.stderr)
    print(f"  Example: {repo_path}/{Path(relative_paths[0]).parent}", file=sys.stderr)
    return None


def cmd_validate_local_path(args):
    """Validate that a local path is NOT inside the skill repository."""
    path = args.path
    force = args.force

    # If force flag is set, skip validation
    if force:
        return 0

    # Get skill repo root (CLAUDE_SKILL_DIR must be set in environment)
    skill_dir = os.environ.get('CLAUDE_SKILL_DIR')
    if not skill_dir:
        print("WARNING: CLAUDE_SKILL_DIR not set, skipping validation", file=sys.stderr)
        return 0

    # Navigate up from skill dir to repo root
    skill_parent = Path(skill_dir).parent.parent
    skill_root = get_git_root(str(skill_parent))

    if not skill_root:
        # Can't detect skill repo, allow
        return 0

    # Get absolute path of target directory
    path_abs = Path(os.path.expanduser(path)).resolve()
    skill_root_path = Path(skill_root).resolve()

    # Check if path is inside skill repo (using Path.is_relative_to for clarity)
    try:
        path_abs.relative_to(skill_root_path)
        # If we get here, path is inside skill repo
        print(f"❌ ERROR: Cannot create artifacts in skill repository ({skill_root})", file=sys.stderr)
        print("Please specify a different directory.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Tip: Use --output-dir flag to force creation in current directory if needed.", file=sys.stderr)
        return 1
    except ValueError:
        # Path is not inside skill repo - good to proceed
        pass

    return 0


def cmd_validate_remote_repo(args):
    """Validate that a remote repository is NOT the skill repository."""
    repo = args.repo

    # Get skill repo remote
    skill_dir = os.environ.get('CLAUDE_SKILL_DIR')
    if not skill_dir:
        print("WARNING: CLAUDE_SKILL_DIR not set, skipping validation", file=sys.stderr)
        return 0

    skill_parent = Path(skill_dir).parent.parent
    skill_root = get_git_root(str(skill_parent))

    if not skill_root:
        # Can't detect skill repo, allow
        return 0

    skill_remote = get_git_remote(skill_root)

    if not skill_remote:
        # Can't detect skill repo remote, allow
        return 0

    # Check if target repo matches skill repo
    if repo == skill_remote:
        print(f"❌ ERROR: Cannot publish to skill repository ({skill_remote})", file=sys.stderr)
        print("Test plans must be published to a separate repository.", file=sys.stderr)
        return 1

    return 0


def cmd_safe_checkout(args):
    """Safely checkout a branch with uncommitted changes check and stale branch detection."""
    repo_path = args.repo_path
    branch = args.branch
    remote = args.remote

    # Expand paths
    repo_path = os.path.expanduser(repo_path)

    # Verify it's a git repo
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        print(f"ERROR: Not a git repository: {repo_path}", file=sys.stderr)
        return 1

    return safe_checkout_branch(repo_path, branch, remote)


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

    # validate-local-path command
    parser_validate_path = subparsers.add_parser(
        "validate-local-path",
        help="Validate that a local path is not inside the skill repository"
    )
    parser_validate_path.add_argument("path", help="Path to validate")
    parser_validate_path.add_argument(
        "--force",
        action="store_true",
        help="Force flag - skip validation"
    )
    parser_validate_path.set_defaults(func=cmd_validate_local_path)

    # validate-remote command
    parser_validate_remote = subparsers.add_parser(
        "validate-remote",
        help="Validate that a remote repository is not the skill repository"
    )
    parser_validate_remote.add_argument(
        "repo",
        help="Remote repository in owner/repo format"
    )
    parser_validate_remote.set_defaults(func=cmd_validate_remote_repo)

    # safe-checkout command
    parser_safe_checkout = subparsers.add_parser(
        "safe-checkout",
        help="Safely checkout a branch with uncommitted changes check and stale branch detection"
    )
    parser_safe_checkout.add_argument("repo_path", help="Path to git repository")
    parser_safe_checkout.add_argument("branch", help="Branch name to checkout")
    parser_safe_checkout.add_argument(
        "--remote",
        default="origin",
        help="Remote name (default: origin)"
    )
    parser_safe_checkout.set_defaults(func=cmd_safe_checkout)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
