#!/usr/bin/env python3
"""
Load odh-test-context JSON for a target repository.

Usage:
    python scripts/load_test_context.py <target_repo> <odh_test_context_path> <feature_dir>

Args:
    target_repo: org/repo, local path, or repo name (last path segment is the JSON stem)
    odh_test_context_path: Path to odh-test-context directory
    feature_dir: Feature directory; write .test_implementation_context.json here when context is found

Output (JSON):
    {
        "target_repo_name": "opendatahub-tests",
        "use_odh_context": true,
        "test_context": { ... } | null
    }
"""

import json
import sys
from pathlib import Path

from scripts.utils.error_utils import exit_error
from scripts.utils.repo_utils import load_repo_test_context


def load_test_context(target_repo: str, odh_test_context_path: str, feature_dir: str) -> dict:
    target_repo_name = Path(target_repo.rstrip("/")).name
    test_context = load_repo_test_context(target_repo_name, odh_test_context_path)

    if test_context is not None:
        context_file = Path(feature_dir) / ".test_implementation_context.json"
        context_file.write_text(json.dumps(test_context, indent=2) + "\n")

    return {
        "target_repo_name": target_repo_name,
        "use_odh_context": test_context is not None,
        "test_context": test_context,
    }


def main():
    if len(sys.argv) != 4:
        exit_error("Usage: python scripts/load_test_context.py <target_repo> <odh_test_context_path> <feature_dir>")

    target_repo = sys.argv[1]
    odh_test_context_path = sys.argv[2]
    feature_dir = sys.argv[3]

    try:
        print(json.dumps(load_test_context(target_repo, odh_test_context_path, feature_dir), indent=2))
    except Exception as e:
        exit_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
