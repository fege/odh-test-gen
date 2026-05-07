#!/usr/bin/env python3
"""
Parse test score assessment file.

Extracts verdict, score, and issues from test quality score markdown files.

Usage:
    python scripts/parse_test_score.py <score_file.md>

Output (JSON):
    {
        "verdict": "Revise",
        "total_score": 5,
        "needs_revision": true,
        "issues": "### Issues Found\n- Missing assertions\n\n### Revision Needed\nAdd assertions"
    }
"""

import json
import re
import sys
from pathlib import Path


def parse_test_score(score_file: str) -> str:
    """
    Parse test score assessment file.

    Args:
        score_file: Path to score markdown file

    Returns:
        JSON string with parsed score data

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    score_path = Path(score_file)

    if not score_path.exists():
        raise FileNotFoundError(f"Score file not found: {score_file}")

    content = score_path.read_text(encoding='utf-8')

    # Extract verdict
    verdict_match = re.search(r'\*\*Verdict\*\*:\s*(\w+)', content)
    verdict = verdict_match.group(1) if verdict_match else 'Unknown'

    # Extract total score
    score_match = re.search(r'\*\*Total Score\*\*:\s*(\d+)/10', content)
    total_score = int(score_match.group(1)) if score_match else 0

    # Extract issues (everything from ### Issues Found to end or next major section)
    issues_match = re.search(
        r'(### Issues Found.*?)(?=\n---|\Z)',
        content,
        re.DOTALL
    )
    issues = issues_match.group(1).strip() if issues_match else None

    # Determine if revision needed
    needs_revision = verdict == 'Revise'

    return json.dumps({
        'verdict': verdict,
        'total_score': total_score,
        'needs_revision': needs_revision,
        'issues': issues,
    }, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/parse_test_score.py <score_file.md>", file=sys.stderr)
        sys.exit(1)

    score_file = sys.argv[1]

    try:
        result = parse_test_score(score_file)
        print(result)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
