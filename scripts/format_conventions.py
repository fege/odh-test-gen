#!/usr/bin/env python3
"""Format test conventions dict as markdown."""
import json
import sys


def format_conventions(conventions: dict) -> str:
    """
    Format conventions dict as markdown.

    Args:
        conventions: Dict from extract_conventions_from_context

    Returns:
        Markdown string
    """
    lines = [
        f"# Test Implementation Conventions for {conventions.get('repo_name', 'Repository')}",
        "",
        "## Framework",
        f"- **{conventions.get('framework', 'unknown')}**",
        "",
        "## File Patterns",
        f"- Test files: `{conventions.get('test_file_pattern', 'test_*.py')}`",
        f"- Test functions: `{conventions.get('test_function_pattern', 'test_*')}`",
        "",
        "## Import Style",
        f"- {conventions.get('import_style', 'Not specified')}",
        "",
    ]

    markers = conventions.get('markers', [])
    if markers:
        lines.extend([
            "## Pytest Markers",
            ""
        ])
        for marker in markers:
            lines.append(f"- `{marker}`")
        lines.append("")

    linting_tools = conventions.get('linting_tools', [])
    if linting_tools and any(linting_tools):
        lines.extend([
            "## Linting Tools",
            ""
        ])
        for tool in linting_tools:
            if tool:
                lines.append(f"- {tool}")
        lines.append("")

    test_dirs = conventions.get('test_directories', [])
    if test_dirs:
        lines.extend([
            "## Test Directories",
            ""
        ])
        for dir in test_dirs:
            lines.append(f"- `{dir}`")
        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/format_conventions.py <conventions.json|-}",
              file=sys.stderr)
        sys.exit(1)

    conventions_file = sys.argv[1]

    try:
        if conventions_file == '-':
            conventions = json.load(sys.stdin)
        else:
            with open(conventions_file, 'r') as f:
                conventions = json.load(f)

        markdown = format_conventions(conventions)
        print(markdown)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
