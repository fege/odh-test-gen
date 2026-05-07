#!/usr/bin/env python3
"""
Component detection and repository mapping.

Extracts components from TestPlan.md frontmatter and content,
then maps them to GitHub repositories.

Usage:
    python scripts/detect_components.py <feature_dir>
"""

import json
import sys
from pathlib import Path

from scripts.utils.component_map import get_repo_for_component
from scripts.utils.frontmatter_utils import read_frontmatter
from scripts.utils.repo_discovery import extract_repo_indicators


def detect_components(feature_dir: str) -> str:
    """
    Detect components and map to repositories.

    Args:
        feature_dir: Path to feature directory containing TestPlan.md

    Returns:
        JSON string with component detection results

    Raises:
        FileNotFoundError: If TestPlan.md is missing
    """
    feature_path = Path(feature_dir)
    testplan_path = feature_path / "TestPlan.md"

    if not testplan_path.exists():
        raise FileNotFoundError(f"TestPlan.md not found at {testplan_path}")

    # --- Extract frontmatter components ---
    frontmatter, _ = read_frontmatter(str(testplan_path))
    frontmatter_components_raw = frontmatter.get('components') or []

    # Preserve original casing (get_repo_for_component handles case-insensitive lookup)
    frontmatter_components = [
        c.strip() for c in frontmatter_components_raw if c
    ]

    # --- Extract content components ---
    tc_dir = feature_path / "test_cases"
    tc_files = [str(f) for f in tc_dir.glob("TC-*.md")] if tc_dir.exists() else []

    # Use existing extraction logic (returns lowercase)
    indicators = extract_repo_indicators(str(testplan_path), tc_files)
    content_components = indicators.get('components', [])

    # --- Merge components (deduplicate case-insensitively, prefer frontmatter casing) ---
    all_components_map = {}
    # Add frontmatter components first (preferred casing)
    for c in frontmatter_components:
        all_components_map[c.lower()] = c
    # Add content components only if not already present
    for c in content_components:
        if c.lower() not in all_components_map:
            all_components_map[c.lower()] = c

    all_components = list(all_components_map.values())

    # --- Map components to repos ---
    repos = {c: get_repo_for_component(c) for c in all_components}

    # --- Get unique repos (excluding None) ---
    unique_repos = list({r for r in repos.values() if r})

    # --- Get repos from frontmatter components (for prioritization) ---
    repos_from_frontmatter = list({repos[c] for c in frontmatter_components if repos.get(c)})

    return json.dumps({
        'frontmatter_components': frontmatter_components,
        'content_components': content_components,
        'all_components': all_components,
        'repos': repos,
        'unique_repos': unique_repos,
        'repos_from_frontmatter': repos_from_frontmatter,
    }, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/detect_components.py <feature_dir>", file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]

    try:
        result = detect_components(feature_dir)
        print(result)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
