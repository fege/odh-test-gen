"""
Filter test cases by automation status and UI category.

Internal module called by get_filtered_tcs.py. Skill users should call
get_filtered_tcs.py instead.

Always returns 3 lists:
- be_test_cases: Backend/non-UI TCs that are NOT implemented
- already_implemented: TCs with automation_status='Complete' and status='Automated'
- ui_test_cases: UI test cases (TC-UI-*) that are NOT implemented
"""

import json
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


def apply_reimplement(result: dict, *, ids: list[str]) -> dict:
    """Move selected already_implemented TCs back into be/ui lists by category.

    Empty ``ids`` is a noop (returns the same dict). IDs not present in
    ``already_implemented`` raise ValueError.
    """
    if not ids:
        return result

    already = result["already_implemented"]
    already_set = set(already)
    unknown = [tc_id for tc_id in ids if tc_id not in already_set]
    if unknown:
        raise ValueError(f"IDs not in already_implemented: {', '.join(unknown)}")

    selected: list[str] = []
    seen: set[str] = set()
    for tc_id in ids:
        if tc_id not in seen:
            seen.add(tc_id)
            selected.append(tc_id)

    be_test_cases = list(result["be_test_cases"])
    ui_test_cases = list(result["ui_test_cases"])

    for tc_id in selected:
        if extract_category_from_tc_id(tc_id) == "ui":
            ui_test_cases.append(tc_id)
        else:
            be_test_cases.append(tc_id)

    return {
        "be_test_cases": be_test_cases,
        "already_implemented": [tc_id for tc_id in already if tc_id not in seen],
        "ui_test_cases": ui_test_cases,
    }


def filter_test_cases(feature_dir: str, tc_ids: list[str]) -> str:
    """
    Filter test cases by automation status first, then by UI category.

    Priority logic:
    1. If automation_status='Complete' and status='Automated' → already_implemented
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

        automation_status = frontmatter.get("automation_status", "").strip().lower()
        status = frontmatter.get("status", "").strip().lower()

        if automation_status == "complete" and status == "automated":
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
