#!/usr/bin/env python3
"""
Filter test cases for implementation. Always re-reads TC files (no cache).

Single entry point for test case filtering in skills. Handles:
- Auto-discovery of TCs if none provided
- Filtering by automation_status and UI category
- Optional re-implement: fold already-implemented TCs back into
  be_test_cases / ui_test_cases (HITL confirmation belongs in the parent skill)

Usage:
    python scripts/get_filtered_tcs.py <feature_dir> [--include-implemented]
        [--reimplement-ids ID,ID] [tc_id ...]

Examples:
    python scripts/get_filtered_tcs.py ~/path/to/feature
    python scripts/get_filtered_tcs.py ~/path/to/feature TC-E2E-001 TC-NEG-001
    python scripts/get_filtered_tcs.py ~/path/to/feature --include-implemented
    python scripts/get_filtered_tcs.py ~/path/to/feature --reimplement-ids TC-E2E-002

Output (JSON):
    {
        "be_test_cases": ["TC-E2E-001"],
        "already_implemented": ["TC-E2E-002"],
        "ui_test_cases": ["TC-UI-001"],
        "next": "proceed"|"prompt_user"
    }
"""

import argparse
import json

from scripts.filter_test_cases import apply_reimplement, filter_test_cases, get_all_tc_ids
from scripts.utils.error_utils import exit_error
from scripts.validate import check_interactive


def decide_reimplement_next(already_implemented: list, *, interactive: bool, skip_prompt: bool) -> str:
    """Return the Step 0.2b action: prompt the user, or skip the re-implement menu."""
    if skip_prompt:
        return "proceed"
    if already_implemented and interactive:
        return "prompt_user"
    return "proceed"


def get_filtered_tcs(
    feature_dir: str,
    tc_ids: list[str] | None = None,
    include_implemented: bool = False,
    reimplement_ids: list[str] | None = None,
) -> dict:
    """
    Filter test cases from live TC files.

    Args:
        feature_dir: Path to feature directory
        tc_ids: Optional list of TC IDs to filter (discovers all if None/empty)
        include_implemented: If True, fold every already_implemented TC back
            into be_test_cases / ui_test_cases by category
        reimplement_ids: Specific already_implemented IDs to fold back.
            Cannot be combined with include_implemented.

    Returns:
        dict with be_test_cases, already_implemented, ui_test_cases lists,
        and next ("proceed" or "prompt_user")
    """
    if include_implemented and reimplement_ids is not None:
        raise ValueError("Cannot combine include_implemented with reimplement_ids")

    if not tc_ids:
        ids = get_all_tc_ids(feature_dir)
    else:
        ids = [part.removesuffix(".md") for item in tc_ids for part in item.replace(",", " ").split()]
        if not ids:
            ids = get_all_tc_ids(feature_dir)

    result = json.loads(filter_test_cases(feature_dir, ids))

    if include_implemented:
        fold_ids = list(result["already_implemented"])
    elif reimplement_ids:
        fold_ids = reimplement_ids
    else:
        fold_ids = []

    result = apply_reimplement(result, ids=fold_ids)
    result["next"] = decide_reimplement_next(
        result["already_implemented"],
        interactive=check_interactive()["interactive"],
        skip_prompt=include_implemented or reimplement_ids is not None,
    )
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Filter test cases for implementation")
    parser.add_argument("feature_dir", help="Path to feature directory")
    parser.add_argument("tc_ids", nargs="*", help="Optional TC IDs to filter")
    parser.add_argument(
        "--include-implemented",
        action="store_true",
        help="Fold all already-implemented TCs back into be/ui lists",
    )
    parser.add_argument(
        "--reimplement-ids",
        metavar="IDS",
        help="Comma-separated already-implemented TC IDs to fold back into be/ui lists",
    )
    args = parser.parse_args()

    tc_ids = args.tc_ids or None

    reimplement_ids = args.reimplement_ids.replace(",", " ").split() if args.reimplement_ids is not None else None

    try:
        result = get_filtered_tcs(
            args.feature_dir,
            tc_ids,
            include_implemented=args.include_implemented,
            reimplement_ids=reimplement_ids,
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        exit_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
