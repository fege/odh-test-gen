#!/usr/bin/env python3
"""
Map component name to test directory path in target repository.

Usage:
    python scripts/get_component_test_dir.py <component_name> <target_repo_path>

Args:
    component_name: Component name from test plan frontmatter
    target_repo_path: Path to target repository

Output:
    Test directory path if component directory exists, otherwise "tests" (fallback)
"""

import os
import sys
from pathlib import Path

from scripts.utils.component_map import get_test_dir_for_component
from scripts.utils.error_utils import exit_error
from scripts.utils.text_utils import sanitize_to_snake_case


def get_component_test_dir(component_name: str, target_repo_path: str) -> str:
    """
    Map component name to test directory path in target repository.

    Strategy:
    1. Try sanitized component name (exact match)
    2. Try component mapping (handles aliases like "AI Core Dashboard" → "ai_hub")
    3. Fall back to "tests"

    Args:
        component_name: Component name from test plan
        target_repo_path: Path to target repository

    Returns:
        Test directory path if exists, otherwise "tests" (fallback)
    """
    tests_base = Path(target_repo_path) / "tests"

    # Try sanitized name first (e.g., "AI Hub" → "ai_hub")
    component_dir_sanitized = sanitize_to_snake_case(component_name)
    component_path = tests_base / component_dir_sanitized

    if component_path.is_dir():
        return f"tests/{component_dir_sanitized}"

    # Try component mapping (handles Jira component aliases)
    component_dir_mapped = get_test_dir_for_component(component_name)
    if component_dir_mapped:
        component_path = tests_base / component_dir_mapped
        if component_path.is_dir():
            return f"tests/{component_dir_mapped}"

    # Fall back to base tests directory
    return "tests"


def main():
    if len(sys.argv) != 3:
        exit_error("Usage: get_component_test_dir.py <component_name> <target_repo_path>")

    component_name = sys.argv[1]
    target_repo_path = sys.argv[2]

    if not os.path.isdir(target_repo_path):
        exit_error(f"Target repo path does not exist: {target_repo_path}")

    test_dir = get_component_test_dir(component_name, target_repo_path)
    print(test_dir)


if __name__ == "__main__":
    main()
