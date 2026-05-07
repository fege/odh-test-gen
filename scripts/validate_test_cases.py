#!/usr/bin/env python3
"""Validate all TC-*.md files in a feature directory."""
import sys
from pathlib import Path
from types import SimpleNamespace
from scripts.frontmatter import cmd_validate


def validate_test_cases(feature_dir: str, schema_type: str) -> int:
    """
    Validate all TC-*.md files in feature_dir/test_cases/.

    Args:
        feature_dir: Path to feature directory
        schema_type: Schema type for validation (e.g., 'test-case')

    Returns:
        0 if all valid, 1 if any invalid
    """
    test_cases_dir = Path(feature_dir) / "test_cases"

    exit_code = 0
    if test_cases_dir.exists():
        for f in test_cases_dir.glob("TC-*.md"):
            try:
                cmd_validate(SimpleNamespace(file=str(f), schema_type=schema_type))
            except SystemExit as e:
                if e.code != 0:
                    exit_code = 1

    return exit_code


def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/validate_test_cases.py <feature_dir> <schema_type>",
              file=sys.stderr)
        sys.exit(1)

    sys.exit(validate_test_cases(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    main()
