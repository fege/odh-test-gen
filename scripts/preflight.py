#!/usr/bin/env python3
"""
Unified preflight checks for test case implementation.

Validates feature directory structure, detects components, maps to repositories,
and locates odh-test-context in one call.

Usage:
    python scripts/preflight.py <feature_dir>

Output (JSON):
    {
        "valid": true,
        "feature_dir": "/path/to/feature",
        "tc_count": 5,
        "testplan_frontmatter": {...},
        "frontmatter_components": ["notebooks", "ai hub"],
        "content_components": ["dashboard"],
        "all_components": [...],
        "repos": {...},
        "unique_repos": [...],
        "repos_from_frontmatter": [...],
        "odh_test_context_path": "/path/to/odh-test-context"
    }
"""

import json
import sys

from scripts.detect_components import detect_components
from scripts.utils.repo_utils import find_known_repo
from scripts.validate_feature_dir import validate_feature_dir


def run_preflight(feature_dir: str) -> str:
    """
    Run all preflight checks.

    Args:
        feature_dir: Path to feature directory

    Returns:
        JSON string with combined results
    """
    # Step 1: Validate directory structure
    validation_result = validate_feature_dir(feature_dir)
    validation_data = json.loads(validation_result)

    # If validation failed, return early
    if not validation_data.get('valid'):
        return validation_result

    # Step 2: Detect components and map to repos
    detection_result = detect_components(feature_dir)
    detection_data = json.loads(detection_result)

    # Step 3: Locate odh-test-context
    try:
        odh_path, _ = find_known_repo('odh-test-context')
    except (ValueError, FileNotFoundError):
        odh_path = None

    # Combine all results
    combined = {
        **validation_data,
        **detection_data,
        'odh_test_context_path': odh_path,
    }

    return json.dumps(combined, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/preflight.py <feature_dir>", file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]

    try:
        result = run_preflight(feature_dir)
        print(result)

        # Exit with appropriate code
        data = json.loads(result)
        sys.exit(0 if data.get('valid') else 1)

    except Exception as e:
        print(json.dumps({
            'valid': False,
            'error': f'Unexpected error: {e}'
        }, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
