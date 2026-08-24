#!/usr/bin/env python3
"""
Map TestPlan.md components to a test directory in the target repository.

Usage:
    python scripts/get_component_test_dir.py <feature_dir> <target_repo_path>
    python scripts/get_component_test_dir.py --teams-only <feature_dir>

Args:
    feature_dir: Path to feature directory containing TestPlan.md
    target_repo_path: Path to target repository

Output:
    Test directory path if a unique component directory exists, otherwise "tests".
    Exits 1 if multiple components map to different existing directories.

    With `--teams-only`, prints a comma-separated, sorted, de-duplicated list of every
    matching `COMPONENT_TEST_DIR_MAP` team name instead (no target repo needed, no
    directory-existence check, no ambiguity error) — used as the `--include-teams` value
    for `validate_test_scope.py`/`detect_boilerplate.py`, where each component's team may
    contribute its own pattern overrides independently of the others.
"""

import os
import sys
from pathlib import Path

from scripts.utils.component_map import get_test_dir_for_component
from scripts.utils.error_utils import exit_error
from scripts.utils.frontmatter_utils import read_frontmatter
from scripts.utils.text_utils import sanitize_to_snake_case

FALLBACK_TEST_DIR = "tests"


class AmbiguousComponentTestDirError(ValueError):
    """Raised when TestPlan components map to more than one existing test directory."""

    def __init__(self, dirs: list[str]):
        self.dirs = dirs
        super().__init__(
            "Multiple test directories match TestPlan components: " + ", ".join(dirs) + ". Ask which directory to use."
        )


def get_frontmatter_components(feature_dir: str) -> list[str]:
    """Return all non-empty components from TestPlan.md frontmatter."""
    testplan_path = Path(feature_dir) / "TestPlan.md"
    if not testplan_path.exists():
        raise FileNotFoundError(f"TestPlan.md not found at {testplan_path}")

    frontmatter, _ = read_frontmatter(str(testplan_path))
    components = frontmatter.get("components") or []

    # Normalize scalar to list (forgive malformed frontmatter)
    if isinstance(components, str):
        components = [components]
    elif not isinstance(components, list):
        components = []

    return [c.strip() for c in components if isinstance(c, str) and c.strip()]


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

    if component_dir_sanitized and component_path.is_dir():
        return f"tests/{component_dir_sanitized}"

    # Try component mapping (handles Jira component aliases)
    component_dir_mapped = get_test_dir_for_component(component_name)
    if component_dir_mapped:
        component_path = tests_base / component_dir_mapped
        if component_path.is_dir():
            return f"tests/{component_dir_mapped}"

    return FALLBACK_TEST_DIR


def get_component_test_dir_for_feature(feature_dir: str, target_repo_path: str) -> str:
    """Map all TestPlan.md components to one test directory.

    Uses every frontmatter component. If they agree on one existing directory
    (including aliases that collapse to the same dir), that directory is returned.
    Components that only fall back to ``tests`` are ignored when a more specific
    directory exists. If two or more distinct existing directories match, raises
    AmbiguousComponentTestDirError.
    """
    components = get_frontmatter_components(feature_dir)
    if not components:
        return FALLBACK_TEST_DIR

    mapped = [get_component_test_dir(component, target_repo_path) for component in components]
    specific = list(dict.fromkeys(d for d in mapped if d != FALLBACK_TEST_DIR))

    if len(specific) == 1:
        test_dir = specific[0]
    elif len(specific) == 0:
        test_dir = FALLBACK_TEST_DIR
    else:
        raise AmbiguousComponentTestDirError(specific)

    return test_dir


def get_teams_for_feature(feature_dir: str) -> str:
    """Comma-separated, sorted, de-duplicated `COMPONENT_TEST_DIR_MAP` teams for every
    TestPlan.md component — unlike `get_component_test_dir_for_feature`, needs no target
    repo and returns ALL matching teams instead of requiring them to agree on one.
    """
    teams = {get_test_dir_for_component(c) for c in get_frontmatter_components(feature_dir)}
    return ",".join(sorted(t for t in teams if t))


def main():
    if len(sys.argv) != 3:
        if "--teams-only" in sys.argv:
            exit_error("Usage: get_component_test_dir.py --teams-only <feature_dir>")
        exit_error("Usage: get_component_test_dir.py <feature_dir> <target_repo_path>")

    # `--teams-only <feature_dir>` skips the target-repo requirement entirely.
    if sys.argv[1] == "--teams-only":
        try:
            print(get_teams_for_feature(sys.argv[2]))
        except FileNotFoundError as e:
            exit_error(str(e))
        return

    feature_dir = sys.argv[1]
    target_repo_path = sys.argv[2]

    if not os.path.isdir(target_repo_path):
        exit_error(f"Target repo path does not exist: {target_repo_path}")

    try:
        test_dir = get_component_test_dir_for_feature(feature_dir, target_repo_path)
    except FileNotFoundError as e:
        exit_error(str(e))
    except AmbiguousComponentTestDirError as e:
        exit_error(str(e))
    print(test_dir)


if __name__ == "__main__":
    main()
