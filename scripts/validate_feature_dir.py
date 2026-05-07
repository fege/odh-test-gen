#!/usr/bin/env python3
"""
Validate feature directory structure.

Checks that a feature directory has all required artifacts:
- TestPlan.md
- test_cases/ directory
- test_cases/INDEX.md
- At least one TC-*.md file

Usage:
    python scripts/validate_feature_dir.py <feature_dir>

Output (JSON):
    {
        "valid": true,
        "feature_dir": "/path/to/feature",
        "testplan_frontmatter": {...},
        "tc_count": 5
    }

    Or on error:
    {
        "valid": false,
        "error": "TestPlan.md not found at /path/to/feature"
    }
"""

import json
import sys
from pathlib import Path

from scripts.utils.frontmatter_utils import read_frontmatter


def validate_feature_dir(feature_dir: str) -> str:
    """
    Validate feature directory structure and read metadata.

    Args:
        feature_dir: Path to feature directory

    Returns:
        JSON string with validation results
    """
    feature_path = Path(feature_dir)

    # Check TestPlan.md exists
    testplan_path = feature_path / "TestPlan.md"
    if not testplan_path.exists():
        return json.dumps({
            'valid': False,
            'error': f'TestPlan.md not found at {testplan_path}'
        }, indent=2)

    # Check test_cases/ directory exists
    tc_dir = feature_path / "test_cases"
    if not tc_dir.exists() or not tc_dir.is_dir():
        return json.dumps({
            'valid': False,
            'error': f'test_cases directory not found at {tc_dir}'
        }, indent=2)

    # Check INDEX.md exists
    index_path = tc_dir / "INDEX.md"
    if not index_path.exists():
        return json.dumps({
            'valid': False,
            'error': f'INDEX.md not found at {index_path}'
        }, indent=2)

    # Check at least one TC-*.md file exists
    tc_files = list(tc_dir.glob("TC-*.md"))
    if not tc_files:
        return json.dumps({
            'valid': False,
            'error': f'No TC-*.md files found in {tc_dir}'
        }, indent=2)

    # Read TestPlan frontmatter
    testplan_frontmatter, _ = read_frontmatter(str(testplan_path))

    # Ensure components is a list (not None)
    if 'components' not in testplan_frontmatter:
        testplan_frontmatter['components'] = []

    return json.dumps({
        'valid': True,
        'feature_dir': str(feature_path),
        'testplan_frontmatter': testplan_frontmatter,
        'tc_count': len(tc_files),
    }, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_feature_dir.py <feature_dir>", file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]

    try:
        result = validate_feature_dir(feature_dir)
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
