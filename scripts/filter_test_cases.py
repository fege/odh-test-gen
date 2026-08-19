"""
Filter test cases by automation status and UI category.

Internal module called by get_filtered_tcs.py. Skill users should call
get_filtered_tcs.py instead.

Always returns 3 lists:
- be_test_cases: Backend/non-UI TCs that are NOT implemented
- already_implemented: TCs with automation_status='Implemented' (UI or non-UI)
- ui_test_cases: UI test cases (TC-UI-*) that are NOT implemented
"""

import json
import os
import sys
from pathlib import Path

from scripts.utils.frontmatter_utils import read_frontmatter
from scripts.utils.tc_parser import extract_category_from_tc_id


def get_all_tc_ids(feature_dir: str) -> list[str]:
    """
    Get all TC IDs from test_cases/ directory.

    Args:
        feature_dir: Path to feature directory

    Returns:
        List of TC IDs (without .md extension)

    Raises:
        FileNotFoundError: If test_cases/ directory doesn't exist
    """
    tc_dir = Path(feature_dir) / "test_cases"

    if not tc_dir.exists():
        raise FileNotFoundError(f"test_cases directory not found: {tc_dir}")

    # Get all TC-*.md files
    tc_files = sorted(tc_dir.glob("TC-*.md"))

    if not tc_files:
        raise FileNotFoundError(f"No TC-*.md files found in {tc_dir}")

    return [tc_file.stem for tc_file in tc_files]


def confirm_re_implement(already_implemented: list[str]) -> bool:
    """
    Ask user whether to re-implement already_implemented test cases.

    Args:
        already_implemented: List of TC IDs that are already implemented

    Returns:
        bool: True if user wants to re-implement, False otherwise
        In non-interactive mode (CLAUDE_NON_INTERACTIVE=true), returns False
    """
    if not already_implemented:
        return False

    is_interactive = os.getenv("CLAUDE_NON_INTERACTIVE", "").lower() not in ("true", "1", "yes")

    if is_interactive:
        print(
            f"\n{len(already_implemented)} test case(s) already implemented: {', '.join(already_implemented)}",
            file=sys.stderr,
        )
        response = input("Re-implement these? [y/n]: ").strip().lower()
        return response in ("y", "yes")
    else:
        # Non-interactive mode: default to NO
        return False


def filter_and_confirm_test_cases(feature_dir: str, tc_ids: list[str] | None = None, confirm: bool = False) -> dict:
    """
    Filter test cases with optional confirmation for re-implementing.

    Args:
        feature_dir: Path to feature directory
        tc_ids: List of test case IDs (if None and confirm=True, auto-discovers all TCs)
        confirm: If True, prompts for re-implement and writes .test_cases_filter.json

    Returns:
        dict with be_test_cases, already_implemented, ui_test_cases lists
    """
    # Auto-discover TCs if no IDs provided
    if tc_ids is None or len(tc_ids) == 0:
        tc_ids = get_all_tc_ids(feature_dir)

    # Filter test cases
    result_json = filter_test_cases(feature_dir, tc_ids or [])
    result = json.loads(result_json)

    # In confirm mode, ask about re-implementing
    if confirm and confirm_re_implement(result["already_implemented"]):
        for tc_id in result["already_implemented"]:
            category = extract_category_from_tc_id(tc_id)
            if category == "ui":
                result["ui_test_cases"].append(tc_id)
            else:
                result["be_test_cases"].append(tc_id)
        result["already_implemented"] = []

    # Always write persistent file
    output_file = Path(feature_dir) / ".test_cases_filter.json"
    output_file.write_text(json.dumps(result, indent=2) + "\n")

    return result


def filter_test_cases(feature_dir: str, tc_ids: list[str]) -> str:
    """
    Filter test cases by automation status first, then by UI category.

    Priority logic:
    1. If automation_status='Implemented' → already_implemented (UI or non-UI)
    2. Else if TC-UI-* → ui_test_cases
    3. Else → be_test_cases (backend/non-UI tests)

    Args:
        feature_dir: Path to feature directory
        tc_ids: List of test case IDs to filter

    Returns:
        JSON string with filtering results:
        {
            "be_test_cases": [...],
            "already_implemented": [...],
            "ui_test_cases": [...]
        }

    Raises:
        FileNotFoundError: If any TC file is missing
    """
    feature_path = Path(feature_dir)
    tc_dir = feature_path / "test_cases"

    be_test_cases = []
    already_implemented = []
    ui_test_cases = []

    for tc_id in tc_ids:
        tc_file = tc_dir / f"{tc_id}.md"

        if not tc_file.exists():
            raise FileNotFoundError(f"{tc_id}.md not found at {tc_file}")

        # Read frontmatter
        frontmatter, _ = read_frontmatter(str(tc_file))

        # Check automation_status FIRST
        automation_status = frontmatter.get("automation_status", "").strip().lower()

        if automation_status == "implemented":
            # Implemented TCs go to already_implemented (UI or not)
            already_implemented.append(tc_id)
        else:
            # Not implemented: check if UI
            category = extract_category_from_tc_id(tc_id)
            if category == "ui":
                ui_test_cases.append(tc_id)
            else:
                be_test_cases.append(tc_id)

    return json.dumps(
        {
            "be_test_cases": be_test_cases,
            "already_implemented": already_implemented,
            "ui_test_cases": ui_test_cases,
        },
        indent=2,
    )
