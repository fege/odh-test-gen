#!/usr/bin/env python3
"""Extract conventions from odh-test-context and format as markdown."""
import json
import sys
from pathlib import Path

from scripts.utils.repo_utils import load_repo_test_context, extract_conventions_from_context
from scripts.format_conventions import format_conventions


def extract_and_format_conventions(
    feature_dir: str,
    repo_name: str,
    odh_test_context_path: str
) -> str:
    """
    Extract conventions and format as markdown.

    Args:
        feature_dir: Feature directory path
        repo_name: Repository name (e.g., 'opendatahub-tests')
        odh_test_context_path: Path to odh-test-context

    Returns:
        Markdown string

    Side effects:
        Writes test_implementation_context.json to feature_dir
    """
    # Load test context
    test_context = load_repo_test_context(repo_name, odh_test_context_path)

    if not test_context:
        return ""

    # Save full context to JSON
    context_file = Path(feature_dir) / "test_implementation_context.json"
    with open(context_file, 'w') as f:
        json.dump(test_context, f, indent=2)

    # Extract and format conventions
    conventions = extract_conventions_from_context(test_context)
    conventions['repo_name'] = repo_name

    markdown = format_conventions(conventions)
    return markdown


def main():
    """CLI entry point."""
    if len(sys.argv) != 4:
        print("Usage: python scripts/extract_and_format_conventions.py <feature_dir> <repo_name> <odh_test_context_path>",
              file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]
    repo_name = sys.argv[2]
    odh_test_context_path = sys.argv[3]

    try:
        markdown = extract_and_format_conventions(feature_dir, repo_name, odh_test_context_path)

        if markdown:
            print(markdown)
        else:
            print(f"# No conventions found for {repo_name}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
