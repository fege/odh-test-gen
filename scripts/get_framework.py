#!/usr/bin/env python3
"""
Get test framework from repository test context.

Usage:
    python scripts/get_framework.py <repo_name_or_org_repo> <odh_test_context_path>

Args:
    repo_name_or_org_repo: Repo name (e.g., 'opendatahub-tests') or org/repo (e.g., 'opendatahub-io/opendatahub-tests')
    odh_test_context_path: Path to odh-test-context directory

Output:
    Framework name (pytest, unittest, playwright, etc.) or "pytest" (default)
"""

import sys

from scripts.utils.error_utils import exit_error
from scripts.utils.repo_utils import get_framework, load_repo_test_context


def main():
    if len(sys.argv) != 3:
        exit_error("Usage: get_framework.py <repo_name_or_org_repo> <odh_test_context_path>")

    repo_input = sys.argv[1]
    odh_test_context_path = sys.argv[2]

    # Extract repo name from org/repo format if present
    repo_name = repo_input.split("/")[-1]

    test_context = load_repo_test_context(repo_name, odh_test_context_path) or {"testing": {"framework": "pytest"}}

    framework = get_framework(test_context)
    print(framework or "pytest")


if __name__ == "__main__":
    main()
