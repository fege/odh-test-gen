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
    uv run python scripts/validate.py category-prefixes <testplan_path>
    uv run python scripts/validate.py interface-types <testplan_path>
    uv run python scripts/validate.py interface-coverage <testplan_path>
    uv run python scripts/validate.py infra-scope <testplan_path>
    uv run python scripts/validate.py tc-counts <feature_dir>
    uv run python scripts/validate.py tc-scope <feature_dir>
    uv run python scripts/validate.py tc-traceability <feature_dir>
    uv run python scripts/validate.py check-interactive
"""

import argparse
import json
import os
import re
import sys
import yaml
from pathlib import Path


from scripts.utils.frontmatter_utils import read_frontmatter, read_frontmatter_validated
from scripts.utils.markdown_utils import extract_section, parse_table_rows
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

    has_content = any(line.strip() for line in section_lines)
    if has_content and not objectives:
        return {
            "valid": False,
            "error": "Section 1.3 has content but no numbered objectives detected (expected: 1. 2. 3. ...)",
        }

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
    missing_headings = [h for h in required if not any(line.startswith(h) for line in lines)]

    pseudo_re = re.compile(r"^\*\*[A-Z][^*]+\*\*:?\s*$")
    pseudo_headings = [
        {"text": line.strip(), "line_number": i + 1} for i, line in enumerate(lines) if pseudo_re.match(line.strip())
    ]

    return {
        "valid": not missing_headings and not pseudo_headings,
        "missing_headings": missing_headings,
        "pseudo_headings": pseudo_headings,
    }


def validate_category_prefixes(testplan_path: str) -> dict:
    """Check Section 5.2 for disallowed TC category prefixes."""
    path = Path(testplan_path)
    if not path.exists():
        return {"valid": False, "error": f"File not found: {testplan_path}"}

    content = path.read_text()
    section_lines, start_line = extract_section(content, "### 5.2 Test Case Naming Convention")
    if not section_lines:
        return {"valid": True, "disallowed": []}

    allowed = set(TESTPLAN_STRUCTURE["allowed_tc_categories"])
    tc_re = re.compile(r"TC-([A-Za-z0-9]+)")

    disallowed = []
    seen = set()
    for i, line in enumerate(section_lines):
        for match in tc_re.finditer(line):
            cat = match.group(1)
            if cat not in allowed and cat not in seen:
                seen.add(cat)
                disallowed.append({"category": cat, "line_number": start_line + i})

    return {"valid": not disallowed, "disallowed": disallowed}


INTERFACE_TABLE_COLUMNS = ["Interface", "Type", "Purpose"]


def validate_interface_types(testplan_path: str) -> dict:
    """Check Section 4 for Config-type entries and correct table columns (no Priority)."""
    path = Path(testplan_path)
    if not path.exists():
        return {"valid": False, "error": f"File not found: {testplan_path}"}

    content = path.read_text()
    section_lines, start_line = extract_section(content, "## 4. Interfaces Under Test")
    if not section_lines:
        return {"valid": True, "config_entries": [], "header": None}

    table_re = re.compile(r"^\|\s*(.+?)\s*\|\s*Config\s*\|", re.IGNORECASE)
    config_entries = []
    header = None
    header_error = None
    for i, line in enumerate(section_lines):
        match = table_re.match(line)
        if match:
            config_entries.append({"interface": match.group(1).strip(), "line_number": start_line + i})

        stripped = line.strip()
        if header is None and stripped.startswith("|") and stripped.endswith("|") and "---" not in stripped:
            columns = [c.strip() for c in stripped.strip("|").split("|")]
            if all(columns):
                header = columns
                if columns != INTERFACE_TABLE_COLUMNS:
                    header_error = {
                        "expected": INTERFACE_TABLE_COLUMNS,
                        "found": columns,
                        "line_number": start_line + i,
                    }

    result = {"valid": not config_entries and header_error is None, "config_entries": config_entries, "header": header}
    if header_error:
        result["header_error"] = header_error
    return result


def validate_interface_coverage(testplan_path: str) -> dict:
    """Check Section 9.2 and Section 6.2 tables list every interface from Section 4."""
    path = Path(testplan_path)
    if not path.exists():
        return {"valid": False, "error": f"File not found: {testplan_path}"}

    content = path.read_text()

    section4_lines, _ = extract_section(content, "## 4. Interfaces Under Test")
    interfaces = [row[0] for row in parse_table_rows(section4_lines) if row and row[0]]

    if not interfaces:
        return {
            "valid": True,
            "interfaces": [],
            "missing_in_9_2": [],
            "missing_in_6_2": [],
            "section_6_2_populated": False,
        }

    section92_lines, _ = extract_section(content, "### 9.2 Interface Coverage")
    covered_92 = {row[0] for row in parse_table_rows(section92_lines) if row and row[0]}
    missing_in_9_2 = [i for i in interfaces if i not in covered_92]

    section62_lines, _ = extract_section(content, "### 6.2 E2E Coverage Matrix")
    rows_62 = parse_table_rows(section62_lines)
    populated_62 = any(row and row[0] for row in rows_62)
    covered_62 = {row[0] for row in rows_62 if row and row[0]}
    missing_in_6_2 = [i for i in interfaces if i not in covered_62] if populated_62 else []

    return {
        "valid": not missing_in_9_2 and not missing_in_6_2,
        "interfaces": interfaces,
        "missing_in_9_2": missing_in_9_2,
        "missing_in_6_2": missing_in_6_2,
        "section_6_2_populated": populated_62,
    }


def validate_infra_scope(testplan_path: str) -> dict:
    """Check Sections 3.1/3.4 for local development tooling indicators."""
    path = Path(testplan_path)
    if not path.exists():
        return {"valid": False, "error": f"File not found: {testplan_path}"}

    content = path.read_text()
    indicators = TESTPLAN_STRUCTURE["dev_tooling_indicators"]
    section_headings = TESTPLAN_STRUCTURE["infra_sections"]

    warnings = []
    seen = set()
    boundary_res = {ind: re.compile(r"(?<![\w-])" + re.escape(ind.casefold()) + r"(?![\w-])") for ind in indicators}
    for heading in section_headings:
        section_lines, start_line = extract_section(content, heading)
        if not section_lines:
            continue
        for i, line in enumerate(section_lines):
            normalized_line = line.casefold()
            for indicator in indicators:
                if boundary_res[indicator].search(normalized_line) and indicator not in seen:
                    seen.add(indicator)
                    warnings.append(
                        {
                            "indicator": indicator,
                            "section": heading,
                            "line_number": start_line + i,
                        }
                    )

    return {"valid": not warnings, "warnings": warnings}


def validate_tc_counts(feature_dir: str) -> dict:
    """Check Section 9.1 TC totals match actual TC file count and row arithmetic."""
    feature_path = Path(feature_dir)
    testplan_path = feature_path / "TestPlan.md"
    tc_dir = feature_path / "test_cases"

    if not testplan_path.exists():
        return {"valid": False, "error": f"TestPlan.md not found at {testplan_path}"}
    if not tc_dir.exists():
        return {"valid": True, "file_count": 0, "table_total": 0, "mismatches": []}

    actual_count = len(list(tc_dir.glob("TC-*.md")))

    content = testplan_path.read_text()
    section_lines, _ = extract_section(content, "### 9.1 Test Case Summary")
    if not section_lines:
        return {"valid": True, "file_count": actual_count, "table_total": 0, "mismatches": []}

    total_re = re.compile(r"^\|\s*\*\*Total\*\*\s*\|\s*\*\*(\d+)\*\*")
    row_re = re.compile(r"^\|\s*TC-\S+\s*\|\s*(\d+)\s*\|")

    table_total = 0
    row_sum = 0
    mismatches = []
    for line in section_lines:
        total_match = total_re.match(line)
        if total_match:
            table_total = int(total_match.group(1))
        row_match = row_re.match(line)
        if row_match:
            row_sum += int(row_match.group(1))

    if table_total > 0 and row_sum != table_total:
        mismatches.append(f"Row sum ({row_sum}) != table total ({table_total})")

    if table_total > 0 and actual_count != table_total:
        mismatches.append(f"TC file count ({actual_count}) != table total ({table_total})")
    if row_sum > 0 and actual_count != row_sum:
        mismatches.append(f"TC file count ({actual_count}) != row sum ({row_sum})")
    if table_total == 0 and row_sum == 0 and actual_count > 0:
        mismatches.append(f"TC files exist ({actual_count}) but no parseable Total/row counts in Section 9.1")

    return {
        "valid": not mismatches,
        "file_count": actual_count,
        "table_total": table_total,
        "row_sum": row_sum,
        "mismatches": mismatches,
    }


def validate_tc_scope(feature_dir: str) -> dict:
    """Check TC-*.md filenames use allowed categories and match frontmatter test_case_id."""
    tc_dir = Path(feature_dir) / "test_cases"
    if not tc_dir.exists():
        return {"valid": True, "checked": 0, "disallowed": [], "id_mismatches": []}

    tc_files = sorted(tc_dir.glob("TC-*.md"))
    if not tc_files:
        return {"valid": True, "checked": 0, "disallowed": [], "id_mismatches": []}

    allowed = set(TESTPLAN_STRUCTURE["allowed_tc_categories"])
    tc_re = re.compile(r"^TC-([A-Z0-9]+)-\d+\.md$")

    disallowed = []
    id_mismatches = []
    for f in tc_files:
        match = tc_re.match(f.name)
        if match and match.group(1) not in allowed:
            disallowed.append({"file": f.name, "category": match.group(1)})

        try:
            frontmatter, _ = read_frontmatter(str(f))
        except (OSError, yaml.YAMLError, ValueError) as e:
            id_mismatches.append({"file": f.name, "error": f"Failed to read frontmatter: {e}"})
            continue

        test_case_id = frontmatter.get("test_case_id")
        if test_case_id != f.stem:
            id_mismatches.append({"file": f.name, "frontmatter_test_case_id": test_case_id})

    return {
        "valid": not disallowed and not id_mismatches,
        "checked": len(tc_files),
        "disallowed": disallowed,
        "id_mismatches": id_mismatches,
    }


def validate_tc_traceability(feature_dir: str) -> dict:
    """Check TC objectives frontmatter traces to Section 1.3 objectives with AC citations."""
    feature_path = Path(feature_dir)
    testplan_path = feature_path / "TestPlan.md"
    if not testplan_path.exists():
        return {"valid": False, "error": f"TestPlan.md not found at {testplan_path}"}

    tc_dir = feature_path / "test_cases"
    if not tc_dir.exists():
        return {"valid": True, "checked": 0, "objectives_found": 0, "errors": []}

    tc_files = sorted(tc_dir.glob("TC-*.md"))
    if not tc_files:
        return {"valid": True, "checked": 0, "objectives_found": 0, "errors": []}

    content = testplan_path.read_text()
    section_lines, _ = extract_section(content, "### 1.3 Test Objectives")

    objective_re = re.compile(r"^(\d+)\.\s+")
    ac_re = re.compile(r"\(AC:\s*")

    objectives = {}
    for line in section_lines:
        match = objective_re.match(line.strip())
        if match:
            num = int(match.group(1))
            objectives[num] = {"text": line.strip(), "has_ac": bool(ac_re.search(line))}

    errors = []
    for f in tc_files:
        try:
            frontmatter, _ = read_frontmatter(str(f))
        except (OSError, yaml.YAMLError, ValueError) as e:
            errors.append({"file": f.name, "error": f"Failed to read frontmatter: {e}"})
            continue

        raw_objectives = frontmatter.get("objectives")
        if not raw_objectives:
            errors.append({"file": f.name, "error": "Missing or empty 'objectives' field"})
            continue

        for raw_num in raw_objectives:
            try:
                num = int(raw_num)
            except (TypeError, ValueError):
                errors.append({"file": f.name, "error": f"Invalid objective reference: {raw_num!r}"})
                continue

            obj = objectives.get(num)
            if obj is None:
                errors.append({"file": f.name, "error": f"References nonexistent objective {num}"})
            elif not obj["has_ac"]:
                errors.append({"file": f.name, "error": f"Objective {num} has no AC citation"})

    return {
        "valid": not errors,
        "checked": len(tc_files),
        "objectives_found": len(objectives),
        "errors": errors,
    }


def check_interactive() -> dict:
    """Check whether the session is interactive or non-interactive (CI).

    Returns dict with:
        interactive: bool — True if interactive, False if non-interactive
        reason: str — which env var triggered non-interactive mode
    """
    ci = os.environ.get("CI", "")
    non_interactive = os.environ.get("CLAUDE_NON_INTERACTIVE", "")

    if non_interactive:
        return {"interactive": False, "reason": "CLAUDE_NON_INTERACTIVE is set"}
    if ci:
        return {"interactive": False, "reason": "CI is set"}
    return {"interactive": True, "reason": "no CI or CLAUDE_NON_INTERACTIVE env var detected"}


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
    category_result = validate_category_prefixes(str(testplan_path))
    interface_result = validate_interface_types(str(testplan_path))
    interface_coverage_result = validate_interface_coverage(str(testplan_path))
    infra_result = validate_infra_scope(str(testplan_path))
    tc_counts_result = validate_tc_counts(feature_dir)
    tc_scope_result = validate_tc_scope(feature_dir)
    tc_traceability_result = validate_tc_traceability(feature_dir)

    valid = (
        all(f["valid"] for f in frontmatter_results)
        and tc_result["valid"]
        and scope_result["valid"]
        and ac_result["valid"]
        and structure_result["valid"]
        and category_result["valid"]
        and interface_result["valid"]
        and interface_coverage_result["valid"]
        and infra_result["valid"]
        and tc_counts_result["valid"]
        and tc_scope_result["valid"]
        and tc_traceability_result["valid"]
    )

    return {
        "valid": valid,
        "frontmatter": frontmatter_results,
        "test_cases": tc_result,
        "scope": scope_result,
        "ac_citations": ac_result,
        "structure": structure_result,
        "category_prefixes": category_result,
        "interface_types": interface_result,
        "interface_coverage": interface_coverage_result,
        "infra_scope": infra_result,
        "tc_counts": tc_counts_result,
        "tc_scope": tc_scope_result,
        "tc_traceability": tc_traceability_result,
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


def cmd_category_prefixes(args):
    result = validate_category_prefixes(args.testplan_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_interface_types(args):
    result = validate_interface_types(args.testplan_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_interface_coverage(args):
    result = validate_interface_coverage(args.testplan_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_infra_scope(args):
    result = validate_infra_scope(args.testplan_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_tc_counts(args):
    result = validate_tc_counts(args.feature_dir)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_tc_scope(args):
    result = validate_tc_scope(args.feature_dir)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_tc_traceability(args):
    result = validate_tc_traceability(args.feature_dir)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


def cmd_check_interactive(_args):
    result = check_interactive()
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["interactive"] else 0)


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

    p_cat = subparsers.add_parser("category-prefixes", help="Check Section 5.2 for disallowed TC categories")
    p_cat.add_argument("testplan_path", help="Path to TestPlan.md")
    p_cat.set_defaults(func=cmd_category_prefixes)

    p_iface = subparsers.add_parser("interface-types", help="Check Section 4 for Config-type entries")
    p_iface.add_argument("testplan_path", help="Path to TestPlan.md")
    p_iface.set_defaults(func=cmd_interface_types)

    p_iface_cov = subparsers.add_parser("interface-coverage", help="Check Section 9.2/6.2 cover Section 4 interfaces")
    p_iface_cov.add_argument("testplan_path", help="Path to TestPlan.md")
    p_iface_cov.set_defaults(func=cmd_interface_coverage)

    p_infra = subparsers.add_parser("infra-scope", help="Check Sections 3.1/3.4 for dev tooling")
    p_infra.add_argument("testplan_path", help="Path to TestPlan.md")
    p_infra.set_defaults(func=cmd_infra_scope)

    p_tc_counts = subparsers.add_parser("tc-counts", help="Check Section 9.1 TC totals match file count")
    p_tc_counts.add_argument("feature_dir", help="Path to feature directory")
    p_tc_counts.set_defaults(func=cmd_tc_counts)

    p_tc_scope = subparsers.add_parser("tc-scope", help="Check TC filenames use allowed categories")
    p_tc_scope.add_argument("feature_dir", help="Path to feature directory")
    p_tc_scope.set_defaults(func=cmd_tc_scope)

    p_tc_trace = subparsers.add_parser("tc-traceability", help="Check TC objectives trace to Section 1.3 + AC")
    p_tc_trace.add_argument("feature_dir", help="Path to feature directory")
    p_tc_trace.set_defaults(func=cmd_tc_traceability)

    p_check_interactive = subparsers.add_parser("check-interactive", help="Check if session is non-interactive (CI)")
    p_check_interactive.set_defaults(func=cmd_check_interactive)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
