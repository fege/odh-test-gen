#!/usr/bin/env python3
"""Detect generic boilerplate phrases in test objectives, priorities, and risks.

Flags generic phrases (e.g. "verify X works as expected", "core functionality") in
Section 1.3 (Test Objectives), Section 2.3 (Test Priorities), and Section 8 (Risks and
Mitigation) of a TestPlan.md. Deterministic, no LLM — the result is passed to
score-agent.md as a precomputed input for the SPECIFICITY rubric criterion.

Usage:
    python scripts/detect_boilerplate.py <test_plan_path> \
        [--include-teams=ai_hub,model_serving] \
        [--checks-dir=scripts/checks]

Always exits 0; results (valid + violations by section) are reported as JSON on stdout.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from scripts.utils.markdown_utils import extract_section
from scripts.utils.schemas import TEMPLATE_HEADINGS
from scripts.utils.validation_config_loader import (
    BOILERPLATE_SECTION_CATEGORIES,
    load_boilerplate_patterns,
    parse_teams_arg,
)


def detect_boilerplate_violations(test_plan_path: str, patterns: dict) -> dict:
    """Find generic boilerplate phrases across Sections 1.3, 2.3, and 8 of test_plan_path.

    Args:
        test_plan_path: Path to TestPlan.md
        patterns: Pattern config dict (as returned by load_boilerplate_patterns), with a
            "patterns" dict of objectives/risks/priorities case-insensitive regex lists.

    Returns:
        {"total_violations": int, "by_section": {section: [violation, ...]}}
        Each violation dict has: file, line, matched_pattern, context, category, violation_type.
    """
    content = Path(test_plan_path).read_text(encoding="utf-8")
    filename = os.path.basename(test_plan_path)
    category_patterns = patterns.get("patterns", {})

    by_section: dict[str, list[dict]] = {}

    for section, category in BOILERPLATE_SECTION_CATEGORIES.items():
        section_lines, start_line = extract_section(content, TEMPLATE_HEADINGS[section])
        if not section_lines:
            continue

        try:
            regexes = [re.compile(p, re.IGNORECASE) for p in category_patterns.get(category, [])]
        except re.error as e:
            raise ValueError(f"Invalid {category} regex pattern: {e}") from e
        if not regexes:
            continue

        # One violation per line, not one per matching regex — two patterns describing the same
        # generic phrasing (e.g. "works as expected" and "works correctly" on one sentence) are
        # one problem, not two.
        section_violations = []
        for i, line in enumerate(section_lines):
            if not line.strip():
                continue
            for regex in regexes:
                if regex.search(line):
                    section_violations.append(
                        {
                            "file": filename,
                            "line": start_line + i,
                            "matched_pattern": regex.pattern,
                            "context": line.strip(),
                            "category": category,
                            "violation_type": "boilerplate_phrase",
                        }
                    )
                    break

        if section_violations:
            by_section[section] = section_violations

    total_violations = sum(len(v) for v in by_section.values())
    return {"total_violations": total_violations, "by_section": by_section}


def load_and_detect(test_plan_path: str, checks_dir: str, teams: list[str] | None = None) -> dict:
    """Load boilerplate patterns and detect violations in test_plan_path.

    Returns:
        {"valid": bool, "total_violations": int, "by_section": {...}} or
        {"valid": False, "error": "..."}
    """
    if not Path(test_plan_path).exists():
        return {"valid": False, "error": f"File not found: {test_plan_path}"}

    try:
        patterns = load_boilerplate_patterns(checks_dir, teams=teams)
        result = detect_boilerplate_violations(test_plan_path, patterns)
    except (OSError, UnicodeError, ValueError) as e:
        return {"valid": False, "error": str(e)}

    return {"valid": result["total_violations"] == 0, **result}


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Detect boilerplate in test plan sections")
    parser.add_argument("test_plan_path", help="Path to TestPlan.md")
    parser.add_argument("--include-teams", default="", help="Comma-separated team names to load patterns from")
    parser.add_argument("--checks-dir", default="scripts/checks", help="Base directory for check config files")

    args = parser.parse_args()

    result = load_and_detect(args.test_plan_path, args.checks_dir, teams=parse_teams_arg(args.include_teams))

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
