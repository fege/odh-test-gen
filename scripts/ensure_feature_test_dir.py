#!/usr/bin/env python3
"""Look for or create a feature package under the component test directory.

Usage:
    python scripts/ensure_feature_test_dir.py <feature_dir> <target_repo_path> <test_dir>

Args:
    feature_dir: Path to feature directory containing TestPlan.md
    target_repo_path: Path to target repository
    test_dir: Component test directory from get_component_test_dir.py (e.g. tests/ai_safety)

Output:
    Relative test directory including the feature package
    (e.g. tests/ai_safety/nemo_guardrails_runtime_state_api).
"""

import os
import sys
from pathlib import Path

from scripts.utils.error_utils import exit_error
from scripts.utils.frontmatter_utils import read_frontmatter
from scripts.utils.text_utils import sanitize_to_snake_case
from scripts.validate import validate_feature_name


def get_feature_name(feature_dir: str) -> str:
    """Return TestPlan.md frontmatter ``feature``, or empty string."""
    testplan_path = Path(feature_dir) / "TestPlan.md"
    if not testplan_path.exists():
        return ""
    frontmatter, _ = read_frontmatter(str(testplan_path))
    raw = frontmatter.get("feature")
    return str(raw).strip() if raw else ""


def resolve_feature_package_name(feature_dir: str) -> str:
    """Snake_case package name from TestPlan ``feature``, else feature_dir basename."""
    raw = get_feature_name(feature_dir)
    if not raw:
        raw = Path(feature_dir).name
    name = sanitize_to_snake_case(raw)
    check = validate_feature_name(name)
    if not check["valid"]:
        raise ValueError(check["error"])
    return name


def ensure_feature_test_dir(feature_dir: str, target_repo_path: str, test_dir: str) -> str:
    """Return ``{test_dir}/{feature}``, creating the package directory if missing.

    If ``test_dir`` already ends with the feature package name, it is returned unchanged.
    When creating a new directory under a Python package (parent has ``__init__.py``),
    an empty ``__init__.py`` is added.
    """
    feature_name = resolve_feature_package_name(feature_dir)
    test_dir = test_dir.strip().rstrip("/")
    if not test_dir:
        raise ValueError("test_dir is empty")

    # Validate test_dir before constructing paths: reject absolute paths
    test_dir_path = Path(test_dir)
    if test_dir_path.is_absolute():
        raise ValueError("test_dir must be relative with no parent directory references")

    if Path(test_dir).name == feature_name:
        return test_dir

    # Validate parent stays within target repo (catches both ".." and symlink escapes)
    parent = Path(target_repo_path) / test_dir
    parent_resolved = parent.resolve()
    target_repo_resolved = Path(target_repo_path).resolve()
    if not parent_resolved.is_relative_to(target_repo_resolved):
        raise ValueError(f"test_dir escapes target repo: {test_dir}")

    if not parent.is_dir():
        raise FileNotFoundError(f"Component test directory does not exist: {parent}")

    dest = parent / feature_name
    dest_resolved = dest.resolve()
    if not dest_resolved.is_relative_to(parent_resolved):
        raise ValueError(f"Feature package path escapes test_dir: {dest}")

    created = not dest.exists()
    if dest.exists() and not dest.is_dir():
        raise NotADirectoryError(f"Feature package path exists and is not a directory: {dest}")

    dest.mkdir(exist_ok=True)
    if created and (parent / "__init__.py").is_file() and not (dest / "__init__.py").exists():
        (dest / "__init__.py").write_text("")

    return f"{test_dir}/{feature_name}"


def main():
    if len(sys.argv) != 4:
        exit_error("Usage: ensure_feature_test_dir.py <feature_dir> <target_repo_path> <test_dir>")

    feature_dir = sys.argv[1]
    target_repo_path = sys.argv[2]
    test_dir = sys.argv[3]

    if not os.path.isdir(target_repo_path):
        exit_error(f"Target repo path does not exist: {target_repo_path}")

    try:
        print(ensure_feature_test_dir(feature_dir, target_repo_path, test_dir))
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        exit_error(str(e))


if __name__ == "__main__":
    main()
