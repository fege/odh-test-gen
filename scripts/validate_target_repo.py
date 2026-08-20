#!/usr/bin/env python3
"""
Validate target repository for test case implementation.

Parses --target-repo flag from arguments and validates it.
Returns default (opendatahub-io/opendatahub-tests) if not provided.

Usage:
    python scripts/validate_target_repo.py [full_arguments_string]

Examples:
    # No arguments → returns default
    python scripts/validate_target_repo.py

    # With --target-repo flag
    python scripts/validate_target_repo.py "feature/path --target-repo ~/my-fork/opendatahub-tests"
"""

import re
import sys
from pathlib import Path

from scripts.parse_skill_args import extract_flag_value
from scripts.utils.error_utils import exit_error

# GitHub owner: 1–39 chars, alphanumeric or hyphen, cannot start/end with hyphen.
# GitHub repo: alphanumeric, hyphen, underscore, or period.
_GITHUB_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_GITHUB_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def get_default_target_repo() -> str:
    """
    Get default target repository when --target-repo flag not provided.

    Returns:
        str: Default repository (opendatahub-io/opendatahub-tests)
    """
    return "opendatahub-io/opendatahub-tests"


def validate_target_repo(repo_name: str) -> dict:
    """
    Validate GitHub repository name format (accepts ANY valid org/repo or full GitHub URLs).

    Args:
        repo_name: Repository name (e.g., "opendatahub-io/opendatahub-tests") or GitHub URL

    Returns:
        dict with validation result:
        {
            "valid": bool,
            "repo": str,
            "error": str (only if invalid)
        }
    """
    # Accept full GitHub URLs, extract org/repo
    if repo_name.startswith("http://") or repo_name.startswith("https://"):
        match = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", repo_name)
        if match:
            repo_name = f"{match.group(1)}/{match.group(2)}"
        else:
            return {"valid": False, "error": "Invalid GitHub URL format"}

    # Validate format: org/repo (no full URLs, no empty parts)
    if not repo_name or "/" not in repo_name:
        return {"valid": False, "error": "Repository must be in format 'org/repo'"}

    parts = repo_name.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return {"valid": False, "error": "Repository must be in format 'org/repo'"}

    owner, repo = parts
    if not _GITHUB_OWNER_RE.fullmatch(owner) or not _GITHUB_REPO_RE.fullmatch(repo):
        return {"valid": False, "error": "Repository must be in format 'org/repo'"}

    return {
        "valid": True,
        "repo": f"{owner}/{repo}",
    }


def validate_target_repo_path(repo_path: str) -> dict:
    """
    Validate local repository path (accepts ANY valid git repo).

    Args:
        repo_path: Local path to repository clone

    Returns:
        dict with validation result:
        {
            "valid": bool,
            "path": str,
            "error": str (only if invalid)
        }
    """
    path = Path(repo_path)

    # Check path exists
    if not path.exists():
        return {"valid": False, "error": f"Path does not exist: {repo_path}"}

    # Check it's a git repo
    git_dir = path / ".git"
    if not git_dir.exists():
        return {"valid": False, "error": f"Not a git repository: {repo_path}"}

    # Accept any valid git repo (escape hatch)
    return {
        "valid": True,
        "path": repo_path,
    }


def extract_target_repo_from_args(args_string: str) -> str | None:
    """Extract --target-repo value using the shared flag parser."""
    value = extract_flag_value(args_string or "", "target-repo")
    return value or None


def main():
    """
    CLI entry point.

    Parses --target-repo from full arguments string and validates it.
    Returns default if not provided.
    """
    # Get full arguments string
    args_string = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None

    # Extract --target-repo value
    target_repo_value = extract_target_repo_from_args(args_string) if args_string else None

    try:
        # If not provided, return default
        if not target_repo_value:
            print(get_default_target_repo())
            return

        # Validate the provided value
        # Try as local path first if it exists
        expanded = str(Path(target_repo_value).expanduser())
        if Path(expanded).exists():
            result = validate_target_repo_path(expanded)
            if result["valid"]:
                print(expanded)
                return
            else:
                exit_error(result["error"])

        # Try as org/repo format
        result = validate_target_repo(target_repo_value)
        if result["valid"]:
            print(result["repo"])
            return
        else:
            exit_error(result["error"])

    except Exception as e:
        exit_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
