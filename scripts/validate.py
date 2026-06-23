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
"""

import argparse
import json
import sys
import yaml
from pathlib import Path

from scripts.utils.frontmatter_utils import read_frontmatter, read_frontmatter_validated
from scripts.utils.schemas import detect_schema_type


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

    valid = all(f["valid"] for f in frontmatter_results) and tc_result["valid"]

    return {
        "valid": valid,
        "frontmatter": frontmatter_results,
        "test_cases": tc_result,
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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
