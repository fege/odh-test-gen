#!/usr/bin/env python3
"""Validate that Section 2.1 Test Levels contains only e2e/UI test types.

Flags disallowed test level names (e.g. "Unit Testing"), test levels that are neither allowed
nor forbidden (e.g. a made-up or misspelled level — an allowlist, not just a denylist), an empty
Section 2.1, and disallowed standalone patterns (e.g. bare "Functional Testing", as opposed to
"functional testing as part of e2e") in Section 2.1 of a TestPlan.md. Deterministic, no LLM — the
result is passed to score-agent.md as a precomputed input for the SCOPE FIDELITY rubric criterion.

Usage:
    python scripts/validate_test_scope.py <test_plan_path> \
        [--include-teams=ai_hub,model_serving] \
        [--checks-dir=scripts/checks]

Always exits 0; results (valid + violations) are reported as JSON on stdout.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from scripts.utils.markdown_utils import extract_section
from scripts.utils.schemas import TEMPLATE_HEADINGS
from scripts.utils.validation_config_loader import load_scope_patterns, parse_teams_arg

SECTION = "2.1"

# Section 2.1 bullets follow the template's fixed format: `- **Level Name** — description`.
_LEVEL_NAME_RE = re.compile(r"^-\s*\*\*(.+?)\*\*")


def _extract_level_name(line: str) -> str | None:
    """Return the bolded test-level name from a Section 2.1 bullet, or None if the line isn't
    one (blank line, prose continuation, placeholder text, etc.).
    """
    match = _LEVEL_NAME_RE.match(line.strip())
    return match.group(1).strip() if match else None


def detect_scope_violations(test_plan_path: str, patterns: dict) -> list[dict]:
    """Find forbidden/unrecognized test levels and forbidden patterns in Section 2.1.

    Args:
        test_plan_path: Path to TestPlan.md
        patterns: Pattern config dict (as returned by load_scope_patterns). Each bullet's
            bolded level name is matched by exact case-insensitive comparison (not substring)
            against allowed_test_levels/forbidden_test_levels; forbidden_patterns are
            case-insensitive regexes scanned across the full line (catches prose mentions too,
            not just declared level names).

    Returns:
        List of violation dicts: file, line, section, matched_pattern, violation_type, context.
        violation_type is one of forbidden_test_level, unrecognized_test_level,
        forbidden_pattern, no_test_levels_declared.
    """
    content = Path(test_plan_path).read_text(encoding="utf-8")
    filename = os.path.basename(test_plan_path)

    section_lines, start_line = extract_section(content, TEMPLATE_HEADINGS[SECTION])
    if not section_lines:
        return []

    allowed_levels = {level.lower() for level in patterns.get("allowed_test_levels", [])}
    forbidden_levels_by_key = {level.lower(): level for level in patterns.get("forbidden_test_levels", [])}
    try:
        forbidden_regexes = [re.compile(p, re.IGNORECASE) for p in patterns.get("forbidden_patterns", [])]
    except re.error as e:
        raise ValueError(f"Invalid forbidden_patterns regex: {e}") from e

    def _violation(line_no: int, matched_pattern: str, violation_type: str, context: str) -> dict:
        return {
            "file": filename,
            "line": line_no,
            "section": SECTION,
            "matched_pattern": matched_pattern,
            "violation_type": violation_type,
            "context": context,
        }

    violations = []
    any_level_declared = False

    for i, line in enumerate(section_lines):
        if not line.strip():
            continue
        line_no = start_line + i
        context = line.strip()

        pattern_hit = False
        for regex in forbidden_regexes:
            if regex.search(line):
                violations.append(_violation(line_no, regex.pattern, "forbidden_pattern", context))
                pattern_hit = True

        level_name = _extract_level_name(line)
        if level_name is None:
            continue
        any_level_declared = True
        level_key = level_name.lower()

        if level_key in forbidden_levels_by_key:
            violations.append(_violation(line_no, forbidden_levels_by_key[level_key], "forbidden_test_level", context))
        elif level_key not in allowed_levels and not pattern_hit:
            # Already flagged via forbidden_patterns above — don't double-report the same bullet.
            violations.append(_violation(line_no, level_name, "unrecognized_test_level", context))

    if not any_level_declared:
        violations.append(
            _violation(start_line, "no_test_levels_declared", "no_test_levels_declared", "Section 2.1 is empty")
        )

    return violations


def load_and_validate(test_plan_path: str, checks_dir: str, teams: list[str] | None = None) -> dict:
    """Load scope patterns and validate test_plan_path against them.

    Returns:
        {"valid": bool, "violations": [...]} or {"valid": False, "error": "..."}
    """
    if not Path(test_plan_path).exists():
        return {"valid": False, "error": f"File not found: {test_plan_path}"}

    try:
        patterns = load_scope_patterns(checks_dir, teams=teams)
        violations = detect_scope_violations(test_plan_path, patterns)
    except (OSError, UnicodeError, ValueError) as e:
        return {"valid": False, "error": str(e)}

    return {"valid": len(violations) == 0, "violations": violations}


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Validate test scope in Section 2.1")
    parser.add_argument("test_plan_path", help="Path to TestPlan.md")
    parser.add_argument("--include-teams", default="", help="Comma-separated team names to load patterns from")
    parser.add_argument("--checks-dir", default="scripts/checks", help="Base directory for check config files")

    args = parser.parse_args()

    result = load_and_validate(args.test_plan_path, args.checks_dir, teams=parse_teams_arg(args.include_teams))

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
