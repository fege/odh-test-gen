#!/usr/bin/env python3
"""Unified validation CLI for test plan artifacts.

Replaces validate_feature_dir.py, validate_gap_counts.py, and
validate_test_cases.py with a single entry point. The ``all``
subcommand orchestrates all checks so skills need only one call.

Usage:
    uv run python scripts/validate.py feature-dir <feature_dir>
    uv run python scripts/validate.py gap-counts <feature_dir> <resolved> <unresolved> <new>
    uv run python scripts/validate.py test-cases <feature_dir>
    uv run python scripts/validate.py all <feature_dir>
    uv run python scripts/validate.py scope-check <testplan_path>
    uv run python scripts/validate.py ac-citations <testplan_path>
    uv run python scripts/validate.py structure <testplan_path>
"""

import argparse
import json
import re
import sys
import yaml
from pathlib import Path


from scripts.utils.frontmatter_utils import read_frontmatter, read_frontmatter_validated
from scripts.utils.markdown_utils import extract_section
from scripts.utils.schemas import TESTPLAN_STRUCTURE, detect_schema_type


def validate_feature_dir(feature_dir: str) -> str:
    """Validate feature directory structure and read metadata.

    Returns JSON string with validation results.
    """
    feature_path = Path(feature_dir)

    testplan_path = feature_path / "TestPlan.md"
    if not testplan_path.exists():
        return json.dumps(
            {
                "valid": False,
                "error": f"TestPlan.md not found at {testplan_path}",
            },
            indent=2,
        )

    tc_dir = feature_path / "test_cases"
    if not tc_dir.exists() or not tc_dir.is_dir():
        return json.dumps(
            {
                "valid": False,
                "error": f"test_cases directory not found at {tc_dir}",
            },
            indent=2,
        )

    index_path = tc_dir / "INDEX.md"
    if not index_path.exists():
        return json.dumps(
            {
                "valid": False,
                "error": f"INDEX.md not found at {index_path}",
            },
            indent=2,
        )

    tc_files = list(tc_dir.glob("TC-*.md"))
    if not tc_files:
        return json.dumps(
            {
                "valid": False,
                "error": f"No TC-*.md files found in {tc_dir}",
            },
            indent=2,
        )

    try:
        testplan_frontmatter, _ = read_frontmatter(str(testplan_path))
    except (OSError, yaml.YAMLError, ValueError) as e:
        return json.dumps(
            {
                "valid": False,
                "error": f"Failed to read TestPlan.md frontmatter: {e}",
            },
            indent=2,
        )
    if "components" not in testplan_frontmatter:
        testplan_frontmatter["components"] = []

    return json.dumps(
        {
            "valid": True,
            "feature_dir": str(feature_path),
            "testplan_frontmatter": testplan_frontmatter,
            "tc_count": len(tc_files),
        },
        indent=2,
    )


def validate_gap_counts(feature_dir: str, resolved: int, unresolved: int, new: int) -> dict:
    """Validate gap count arithmetic: unresolved == original - resolved + new.

    Returns dict with validation results.
    """
    gaps_file = Path(feature_dir) / "TestPlanGaps.md"
    if not gaps_file.exists():
        return {"valid": False, "error": f"{gaps_file} not found"}

    try:
        frontmatter, _ = read_frontmatter_validated(str(gaps_file), "test-gaps")
        original = frontmatter.get("gap_count", 0)
    except Exception as e:
        return {"valid": False, "error": f"Failed to read gap count: {e}"}

    expected = original - resolved + new

    result = {
        "original": original,
        "resolved": resolved,
        "unresolved": unresolved,
        "new": new,
        "expected": expected,
    }

    if unresolved == expected:
        return {"valid": True, **result}
    else:
        return {"valid": False, **result}


def validate_test_cases(feature_dir: str, schema_type: str = "test-case") -> dict:
    """Validate all TC-*.md files in feature_dir/test_cases/.

    Returns dict with validation results.
    """
    test_cases_dir = Path(feature_dir) / "test_cases"
    if not test_cases_dir.exists():
        return {"valid": True, "checked": 0, "failed": 0, "errors": []}

    tc_files = list(test_cases_dir.glob("TC-*.md"))
    if not tc_files:
        return {"valid": True, "checked": 0, "failed": 0, "errors": []}

    if not (test_cases_dir / "INDEX.md").exists():
        return {
            "valid": False,
            "checked": 0,
            "failed": 0,
            "errors": [{"file": "INDEX.md", "error": "INDEX.md not found in test_cases/"}],
        }

    errors = []
    for f in tc_files:
        try:
            read_frontmatter_validated(str(f), schema_type)
        except Exception as e:
            errors.append({"file": str(f), "error": str(e)})

    return {
        "valid": not errors,
        "checked": len(tc_files),
        "failed": len(errors),
        "errors": errors,
    }


def validate_scope(testplan_path: str) -> dict:
    """Check Section 2.1 for disallowed test level names."""
    path = Path(testplan_path)
    if not path.exists():
        return {"valid": False, "error": f"File not found: {testplan_path}"}

    content = path.read_text()
    section_lines, start_line = extract_section(content, "### 2.1 Test Levels")
    if not section_lines:
        return {"valid": True, "violations": []}

    violations = [
        {"level": level_name, "line_number": start_line + i}
        for i, line in enumerate(section_lines)
        for level_name in TESTPLAN_STRUCTURE["disallowed_test_levels"]
        if f"**{level_name}**" in line
    ]

    return {"valid": not violations, "violations": violations}


def validate_ac_citations(testplan_path: str) -> dict:
    """Check Section 1.3 objectives for (AC: ...) citations."""
    path = Path(testplan_path)
    if not path.exists():
        return {"valid": False, "error": f"File not found: {testplan_path}"}

    content = path.read_text()
    section_lines, start_line = extract_section(content, "### 1.3 Test Objectives")
    if not section_lines:
        return {"valid": True, "total": 0, "cited": 0, "uncited": []}

    objective_re = re.compile(r"^\d+\.\s+")
    ac_re = re.compile(r"\(AC:\s*")

    objectives = [
        {"text": line.strip(), "line_number": start_line + i}
        for i, line in enumerate(section_lines)
        if objective_re.match(line.strip())
    ]

    uncited = [obj for obj in objectives if not ac_re.search(obj["text"])]
    cited = len(objectives) - len(uncited)

    return {
        "valid": not uncited,
        "total": len(objectives),
        "cited": cited,
        "uncited": uncited,
    }


def validate_structure(testplan_path: str) -> dict:
    """Check TestPlan.md for required headings and bold-text pseudo-headings."""
    path = Path(testplan_path)
    if not path.exists():
        return {"valid": False, "error": f"File not found: {testplan_path}"}

    content = path.read_text()
    lines = content.splitlines()

    required = [s["heading"] for s in TESTPLAN_STRUCTURE["sections"] if s["required"]]
    missing_headings = [h for h in required if all(h not in line for line in lines)]

    pseudo_re = re.compile(r"^\*\*[A-Z][^*]+\*\*:?\s*$")
    pseudo_headings = [
        {"text": line.strip(), "line_number": i + 1} for i, line in enumerate(lines) if pseudo_re.match(line.strip())
    ]

    return {
        "valid": not missing_headings and not pseudo_headings,
        "missing_headings": missing_headings,
        "pseudo_headings": pseudo_headings,
    }


def validate_all(feature_dir: str) -> dict:
    """Run all validations on a feature directory.

    Only TestPlan.md is required. TestPlanGaps.md and test_cases/ are
    validated when present but their absence is not a failure.
    """
    feature_path = Path(feature_dir)

    testplan_path = feature_path / "TestPlan.md"
    if not testplan_path.exists():
        return {"valid": False, "error": f"TestPlan.md not found at {testplan_path}"}

    frontmatter_results = []
    for artifact in ["TestPlan.md", "TestPlanGaps.md"]:
        path = feature_path / artifact
        if not path.exists():
            continue
        try:
            read_frontmatter_validated(str(path), detect_schema_type(str(path)))
            frontmatter_results.append({"file": artifact, "valid": True})
        except Exception as e:
            frontmatter_results.append({"file": artifact, "valid": False, "error": str(e)})

    tc_result = validate_test_cases(feature_dir)
    scope_result = validate_scope(str(testplan_path))
    ac_result = validate_ac_citations(str(testplan_path))
    structure_result = validate_structure(str(testplan_path))

    valid = (
        all(f["valid"] for f in frontmatter_results)
        and tc_result["valid"]
        and scope_result["valid"]
        and ac_result["valid"]
        and structure_result["valid"]
    )

    return {
        "valid": valid,
        "frontmatter": frontmatter_results,
        "test_cases": tc_result,
        "scope": scope_result,
        "ac_citations": ac_result,
        "structure": structure_result,
    }


def cmd_feature_dir(args):
    result = validate_feature_dir(args.feature_dir)
    print(result)
    data = json.loads(result)
    sys.exit(0 if data.get("valid") else 1)


def cmd_gap_counts(args):
    result = validate_gap_counts(args.feature_dir, args.resolved, args.unresolved, args.new)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_test_cases(args):
    result = validate_test_cases(args.feature_dir, args.schema_type)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_all(args):
    result = validate_all(args.feature_dir)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_scope_check(args):
    result = validate_scope(args.testplan_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_ac_citations(args):
    result = validate_ac_citations(args.testplan_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_structure(args):
    result = validate_structure(args.testplan_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def main():
    parser = argparse.ArgumentParser(
        description="Unified validation CLI for test plan artifacts",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_feature = subparsers.add_parser("feature-dir", help="Validate feature directory structure")
    p_feature.add_argument("feature_dir", help="Path to feature directory")
    p_feature.set_defaults(func=cmd_feature_dir)

    p_gaps = subparsers.add_parser("gap-counts", help="Validate gap count arithmetic")
    p_gaps.add_argument("feature_dir", help="Path to feature directory")
    p_gaps.add_argument("resolved", type=int, help="Gaps resolved")
    p_gaps.add_argument("unresolved", type=int, help="Gaps still unresolved")
    p_gaps.add_argument("new", type=int, help="New gaps identified")
    p_gaps.set_defaults(func=cmd_gap_counts)

    p_tc = subparsers.add_parser("test-cases", help="Validate all TC-*.md frontmatter")
    p_tc.add_argument("feature_dir", help="Path to feature directory")
    p_tc.add_argument("schema_type", nargs="?", default="test-case", help="Schema type (default: test-case)")
    p_tc.set_defaults(func=cmd_test_cases)

    p_all = subparsers.add_parser("all", help="Run all validations on a feature directory")
    p_all.add_argument("feature_dir", help="Path to feature directory")
    p_all.set_defaults(func=cmd_all)

    p_scope = subparsers.add_parser("scope-check", help="Check Section 2.1 for disallowed test levels")
    p_scope.add_argument("testplan_path", help="Path to TestPlan.md")
    p_scope.set_defaults(func=cmd_scope_check)

    p_ac = subparsers.add_parser("ac-citations", help="Check Section 1.3 objectives for AC citations")
    p_ac.add_argument("testplan_path", help="Path to TestPlan.md")
    p_ac.set_defaults(func=cmd_ac_citations)

    p_struct = subparsers.add_parser("structure", help="Check required headings and pseudo-heading violations")
    p_struct.add_argument("testplan_path", help="Path to TestPlan.md")
    p_struct.set_defaults(func=cmd_structure)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
