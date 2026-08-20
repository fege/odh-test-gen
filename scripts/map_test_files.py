#!/usr/bin/env python3
"""
Map test cases to test files based on organization strategy.

Determines file organization (by-category, one-per-tc, etc.) and maps
each TC to a test file path and function name.

Usage:
    python scripts/map_test_files.py <feature_dir> <strategy> <test_dir> [--feature-name NAME] [--tc-ids TC1,TC2,...]

Strategies:
    - one-per-tc: One file per test case
    - by-category: Group by category (TC-NEG, TC-E2E, etc.) as a filename prefix
    - by-category-with-subdirs: Alias of by-category. TC prefixes are never directories.

TCs with status=Automated, automation_status=Complete, and a non-empty
automation_file keep that path (re-implement rewrites the existing file).

Output (JSON):
    {
        "file_mapping": [
            {
                "file_path": "tests/test_neg_notebooks.py",
                "test_cases": ["TC-NEG-001", "TC-NEG-002"],
                "function_names": ["test_create_notebook", "test_delete_notebook"]
            }
        ],
        "strategy": "by-category",
        "total_test_cases": 2,
        "total_files": 1
    }
"""

import json
import sys
from pathlib import Path

from scripts.utils.error_utils import exit_error
from scripts.utils.frontmatter_utils import read_frontmatter
from scripts.utils.tc_parser import extract_category_from_tc_id, extract_title_from_tc_file
from scripts.utils.text_utils import sanitize_to_snake_case


def _validate_tc_file(tc_dir: Path, tc_id: str) -> Path:
    """Validate TC file exists and return path."""
    tc_file = tc_dir / f"{tc_id}.md"
    if not tc_file.exists():
        raise FileNotFoundError(f"{tc_id}.md not found at {tc_file}")
    return tc_file


def _generate_function_name(tc_file: Path) -> str:
    """Generate test function name from TC file."""
    title = extract_title_from_tc_file(str(tc_file))
    sanitized = sanitize_to_snake_case(title)
    return f"test_{sanitized}"


def _is_reimplement(frontmatter: dict) -> bool:
    automation_status = str(frontmatter.get("automation_status") or "").strip().lower()
    status = str(frontmatter.get("status") or "").strip().lower()
    return automation_status == "complete" and status == "automated"


def _recorded_automation_file(frontmatter: dict) -> str | None:
    raw = frontmatter.get("automation_file")
    if raw is None:
        return None
    path = str(raw).strip()
    return path or None


def _recorded_function_name(frontmatter: dict, tc_file: Path) -> str:
    raw = frontmatter.get("automation_function")
    if raw is not None:
        name = str(raw).strip()
        if name:
            return name
    return _generate_function_name(tc_file)


def _merge_file_mapping(primary: list[dict], extra: list[dict]) -> list[dict]:
    """Append extra entries, combining those that share file_path."""
    by_path = {entry["file_path"]: entry for entry in primary}
    merged = list(primary)
    for entry in extra:
        existing = by_path.get(entry["file_path"])
        if existing is None:
            merged.append(entry)
            by_path[entry["file_path"]] = entry
            continue
        existing["test_cases"].extend(entry["test_cases"])
        existing["function_names"].extend(entry["function_names"])
    return merged


def _split_reimplement(tc_dir: Path, tc_ids: list[str]) -> tuple[list[dict], list[str]]:
    """Map Complete+Automated TCs to recorded automation_file; return leftover IDs."""
    by_file: dict[str, dict] = {}
    order: list[str] = []
    remaining: list[str] = []

    for tc_id in tc_ids:
        tc_file = _validate_tc_file(tc_dir, tc_id)
        frontmatter, _ = read_frontmatter(str(tc_file))
        auto_file = _recorded_automation_file(frontmatter)
        if _is_reimplement(frontmatter) and auto_file:
            if auto_file not in by_file:
                order.append(auto_file)
                by_file[auto_file] = {"file_path": auto_file, "test_cases": [], "function_names": []}
            by_file[auto_file]["test_cases"].append(tc_id)
            by_file[auto_file]["function_names"].append(_recorded_function_name(frontmatter, tc_file))
        else:
            remaining.append(tc_id)

    return [by_file[path] for path in order], remaining


def _map_one_per_tc(tc_dir: Path, tc_ids: list[str], test_dir: str, _feature_name: str | None = None) -> list[dict]:
    """Strategy: One file per test case."""
    for tc_id in tc_ids:
        _validate_tc_file(tc_dir, tc_id)

    return [
        {
            "file_path": f"{test_dir}/test_{tc_id.lower().replace('-', '_')}.py",
            "test_cases": [tc_id],
            "function_names": [f"test_{tc_id.lower().replace('-', '_')}"],
        }
        for tc_id in tc_ids
    ]


def _map_by_category(tc_dir: Path, tc_ids: list[str], test_dir: str, feature_name: str) -> list[dict]:
    """Strategy: Group by category as a filename prefix, never as a directory."""
    category_groups: dict[str, list[str]] = {}

    for tc_id in tc_ids:
        _validate_tc_file(tc_dir, tc_id)
        category = extract_category_from_tc_id(tc_id)
        category_groups.setdefault(category, []).append(tc_id)

    file_mapping = []
    for category, tc_list in category_groups.items():
        file_path = f"{test_dir}/test_{category}_{feature_name}.py"
        function_names = [_generate_function_name(tc_dir / f"{tc_id}.md") for tc_id in tc_list]
        file_mapping.append(
            {
                "file_path": file_path,
                "test_cases": tc_list,
                "function_names": function_names,
            }
        )

    return file_mapping


# Strategy dispatch. by-category-with-subdirs is an alias: TC prefixes (e2e, neg, nfr)
# are never created as directories.
_STRATEGIES = {
    "one-per-tc": _map_one_per_tc,
    "by-category": _map_by_category,
    "by-category-with-subdirs": _map_by_category,
}


def map_test_files(
    feature_dir: str, tc_ids: list[str], strategy: str, test_dir: str = "tests", feature_name: str = "feature"
) -> str:
    """
    Map test cases to test files based on organization strategy.

    Args:
        feature_dir: Path to feature directory
        tc_ids: List of test case IDs
        strategy: Organization strategy (one-per-tc, by-category, by-category-with-subdirs)
        test_dir: Test directory path (default: "tests")
        feature_name: Feature name for file naming (default: "feature")

    Returns:
        JSON string with file mapping results

    Raises:
        FileNotFoundError: If any TC file is missing
    """
    feature_path = Path(feature_dir)
    tc_dir = feature_path / "test_cases"

    strategy_fn = _STRATEGIES.get(strategy)
    if not strategy_fn:
        raise ValueError(f"Invalid strategy: {strategy}")

    reimplement_mapping, remaining = _split_reimplement(tc_dir, tc_ids)
    file_mapping = list(reimplement_mapping)
    if remaining:
        file_mapping = _merge_file_mapping(file_mapping, strategy_fn(tc_dir, remaining, test_dir, feature_name))

    return json.dumps(
        {
            "file_mapping": file_mapping,
            "strategy": strategy,
            "total_test_cases": len(tc_ids),
            "total_files": len(file_mapping),
        },
        indent=2,
    )


def main():
    """CLI entry point."""
    if len(sys.argv) < 4:
        exit_error(
            "Usage: python scripts/map_test_files.py <feature_dir> <strategy>"
            " <test_dir> [--feature-name NAME] [--tc-ids TC1,TC2,...]"
        )

    feature_dir = sys.argv[1]
    strategy = sys.argv[2]
    test_dir = sys.argv[3]

    # Parse optional arguments
    feature_name = "feature"
    tc_ids = []

    i = 4
    while i < len(sys.argv):
        if sys.argv[i] == "--feature-name" and i + 1 < len(sys.argv):
            feature_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--tc-ids" and i + 1 < len(sys.argv):
            tc_ids = sys.argv[i + 1].split(",")
            i += 2
        else:
            i += 1

    try:
        result = map_test_files(feature_dir, tc_ids, strategy, test_dir, feature_name)
        print(result)
    except (FileNotFoundError, ValueError) as e:
        exit_error(f"Error: {e}")
    except Exception as e:
        exit_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
