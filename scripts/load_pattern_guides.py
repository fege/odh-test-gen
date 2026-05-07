#!/usr/bin/env python3
"""
Load repository instructions and testing pattern guides.

Searches for CLAUDE.md, AGENTS.md, CONSTITUTION.md and framework-specific
pattern guides in .claude/rules/.

Usage:
    python scripts/load_pattern_guides.py <repo_path> <framework>

Output (JSON):
    {
        "repo_instructions_files": ["CLAUDE.md", ".claude/AGENTS.md"],
        "repo_instructions_content": "...",
        "pattern_guide_files": [".claude/rules/pytest-tests.md"],
        "pattern_guide_content": "...",
        "needs_generation": false
    }
"""

import json
import sys
from pathlib import Path


def load_pattern_guides(repo_path: str, framework: str) -> str:
    """
    Load repository instructions and pattern guides.

    Args:
        repo_path: Path to code repository
        framework: Test framework (pytest, go, jest, etc.)

    Returns:
        JSON string with loaded guides and generation status
    """
    repo = Path(repo_path)

    # Check for repository-specific instruction files
    repo_instructions_files = []
    repo_instructions_content = []

    for filename in ['CLAUDE.md', 'AGENTS.md', 'CONSTITUTION.md']:
        # Check .claude/ first, then root
        claude_file = repo / '.claude' / filename
        root_file = repo / filename

        if claude_file.exists():
            repo_instructions_files.append(f".claude/{filename}")
            repo_instructions_content.append(claude_file.read_text(encoding='utf-8'))
        elif root_file.exists():
            repo_instructions_files.append(filename)
            repo_instructions_content.append(root_file.read_text(encoding='utf-8'))

    # Combine repo instructions
    combined_repo_instructions = '\n\n'.join([
        f"## From {fname}\n\n{content}"
        for fname, content in zip(repo_instructions_files, repo_instructions_content)
    ]) if repo_instructions_content else None

    # Check for pattern guides in .claude/rules/
    pattern_guide_files = []
    pattern_guide_content = []
    rules_dir = repo / '.claude' / 'rules'

    if rules_dir.exists():
        # Framework-specific pattern guide
        framework_guide = rules_dir / f"{framework}-tests.md"
        if framework_guide.exists():
            pattern_guide_files.append(str(framework_guide.relative_to(repo)))
            pattern_guide_content.append(framework_guide.read_text(encoding='utf-8'))

        # General testing standards
        standards_file = rules_dir / "testing-standards.md"
        if standards_file.exists():
            pattern_guide_files.append(str(standards_file.relative_to(repo)))
            pattern_guide_content.append(standards_file.read_text(encoding='utf-8'))

    # Combine pattern guides
    combined_pattern_guides = '\n\n'.join(pattern_guide_content) if pattern_guide_content else None

    # Determine if generation is needed
    needs_generation = len(pattern_guide_files) == 0

    return json.dumps({
        'repo_instructions_files': repo_instructions_files,
        'repo_instructions_content': combined_repo_instructions,
        'pattern_guide_files': pattern_guide_files,
        'pattern_guide_content': combined_pattern_guides,
        'needs_generation': needs_generation,
    }, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) != 3:
        print("Usage: python scripts/load_pattern_guides.py <repo_path> <framework>",
              file=sys.stderr)
        sys.exit(1)

    repo_path = sys.argv[1]
    framework = sys.argv[2]

    try:
        result = load_pattern_guides(repo_path, framework)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
