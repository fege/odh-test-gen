"""Utilities for parsing markdown section content."""

import re


def extract_section(content: str, heading: str) -> tuple[list[str], int]:
    """Extract lines between a heading and the next heading of equal or higher level.

    Returns (lines, start_line_number) where start_line_number is 1-indexed.
    Returns ([], 0) if the heading is not found.
    """
    lines = content.splitlines()
    level = max(heading.count("#"), 1)
    pattern = re.compile(r"^#{1," + str(level) + r"}\s")
    start = None
    for i, line in enumerate(lines):
        if line.startswith(heading):
            start = i + 1
            continue
        if start is not None and pattern.match(line):
            return lines[start:i], start + 1
    if start is not None:
        return lines[start:], start + 1
    return [], 0


def parse_table_rows(section_lines: list) -> list:
    """Parse the first markdown table in section_lines, skipping header and separator rows.

    Returns a list of rows, each a list of cell strings.
    """
    rows = []
    header_skipped = False
    separator_re = re.compile(r"^:?-+:?$")
    for line in section_lines:
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            if header_skipped:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not header_skipped:
            header_skipped = True
            continue
        if all(separator_re.match(c) for c in cells):
            continue
        rows.append(cells)
    return rows
