#!/usr/bin/env python3
"""
Map test cases to test files based on organization strategy.

Determines file organization (by-category, one-per-tc, etc.) and maps
each TC to a test file path and function name.

Usage:
    python scripts/map_test_files.py <feature_dir> <strategy> <test_dir> [--feature-name NAME] [--tc-ids TC1,TC2,...]

Strategies:
    - one-per-tc: One file per test case
    - by-category: Group by category (TC-API, TC-E2E, etc.)
    - by-category-with-subdirs: Categories in subdirectories

Output (JSON):
    {
        "file_mapping": [
            {
                "file_path": "tests/test_api_notebooks.py",
                "test_cases": ["TC-API-001", "TC-API-002"],
                "function_names": ["test_create_notebook", "test_delete_notebook"]
            }
        ],
        "strategy": "by-category",
        "total_test_cases": 2,
        "total_files": 1
    }
"""

import json
import sys
from functools import partial
from pathlib import Path
from typing import Dict, List

from scripts.utils.tc_parser import extract_category_from_tc_id, extract_title_from_tc_file
from scripts.utils.text_utils import sanitize_to_snake_case


def _validate_tc_file(tc_dir: Path, tc_id: str) -> Path:
    """Validate TC file exists and return path."""
    tc_file = tc_dir / f"{tc_id}.md"
    if not tc_file.exists():
        raise FileNotFoundError(f"{tc_id}.md not found at {tc_file}")
    return tc_file


def _generate_function_name(tc_file: Path) -> str:
    """Generate test function name from TC file."""
    title = extract_title_from_tc_file(str(tc_file))
    sanitized = sanitize_to_snake_case(title)
    return f"test_{sanitized}"


def _map_one_per_tc(tc_dir: Path, tc_ids: List[str], test_dir: str, _feature_name: str = None) -> List[Dict]:
    """Strategy: One file per test case."""
    # Validate all files first
    for tc_id in tc_ids:
        _validate_tc_file(tc_dir, tc_id)

    # Generate mapping
    return [
        {
            'file_path': f"{test_dir}/test_{tc_id.lower().replace('-', '_')}.py",
            'test_cases': [tc_id],
            'function_names': [f"test_{tc_id.lower().replace('-', '_')}"],
        }
        for tc_id in tc_ids
    ]


def _map_by_category(tc_dir: Path, tc_ids: List[str], test_dir: str, feature_name: str, use_subdirs: bool = False) -> List[Dict]:
    """Strategy: Group by category, optionally with subdirectories."""
    category_groups: Dict[str, List[str]] = {}

    # Group and validate TCs
    for tc_id in tc_ids:
        _validate_tc_file(tc_dir, tc_id)
        category = extract_category_from_tc_id(tc_id)
        category_groups.setdefault(category, []).append(tc_id)

    # Generate mapping for each category
    file_mapping = []
    for category, tc_list in category_groups.items():
        file_path = f"{test_dir}/{category}/test_{feature_name}.py" if use_subdirs else f"{test_dir}/test_{category}_{feature_name}.py"

        function_names = [
            _generate_function_name(tc_dir / f"{tc_id}.md")
            for tc_id in tc_list
        ]

        file_mapping.append({
            'file_path': file_path,
            'test_cases': tc_list,
            'function_names': function_names,
        })

    return file_mapping


# Strategy dispatch
_STRATEGIES = {
    'one-per-tc': _map_one_per_tc,
    'by-category': partial(_map_by_category, use_subdirs=False),
    'by-category-with-subdirs': partial(_map_by_category, use_subdirs=True),
}


def map_test_files(
    feature_dir: str,
    tc_ids: List[str],
    strategy: str,
    test_dir: str = "tests",
    feature_name: str = "feature"
) -> str:
    """
    Map test cases to test files based on organization strategy.

    Args:
        feature_dir: Path to feature directory
        tc_ids: List of test case IDs
        strategy: Organization strategy (one-per-tc, by-category, by-category-with-subdirs)
        test_dir: Test directory path (default: "tests")
        feature_name: Feature name for file naming (default: "feature")

    Returns:
        JSON string with file mapping results

    Raises:
        FileNotFoundError: If any TC file is missing
    """
    feature_path = Path(feature_dir)
    tc_dir = feature_path / "test_cases"

    # Dispatch to strategy function
    strategy_fn = _STRATEGIES.get(strategy)
    if not strategy_fn:
        raise ValueError(f"Invalid strategy: {strategy}")

    file_mapping = strategy_fn(tc_dir, tc_ids, test_dir, feature_name)

    return json.dumps({
        'file_mapping': file_mapping,
        'strategy': strategy,
        'total_test_cases': len(tc_ids),
        'total_files': len(file_mapping),
    }, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) < 4:
        print("Usage: python scripts/map_test_files.py <feature_dir> <strategy> <test_dir> [--feature-name NAME] [--tc-ids TC1,TC2,...]",
              file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]
    strategy = sys.argv[2]
    test_dir = sys.argv[3]

    # Parse optional arguments
    feature_name = "feature"
    tc_ids = []

    i = 4
    while i < len(sys.argv):
        if sys.argv[i] == '--feature-name' and i + 1 < len(sys.argv):
            feature_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--tc-ids' and i + 1 < len(sys.argv):
            tc_ids = sys.argv[i + 1].split(',')
            i += 2
        else:
            i += 1

    try:
        result = map_test_files(feature_dir, tc_ids, strategy, test_dir, feature_name)
        print(result)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
