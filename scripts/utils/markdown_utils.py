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


def extract_headings(content: str) -> list[str]:
    """Return all markdown heading lines (lines starting with ``#`` followed by a space)."""
    return [line for line in content.splitlines() if re.match(r"^#{1,6}\s", line)]


_TABLE_CELL_PLACEHOLDERS = {"-", "n/a", "tbd"}


def is_filled_cell(value: str) -> bool:
    """True if a table cell holds real content, not blank or a placeholder marker (-, N/A, TBD)."""
    return bool(value) and value.casefold() not in _TABLE_CELL_PLACEHOLDERS


def parse_numbered_objectives(lines: list) -> list:
    """Parse a numbered list (``N. text``), joining each item with its wrapped continuation lines.

    Returns a list of dicts ``{"num": int, "text": str, "line_index": int}`` where ``line_index``
    is the 0-based offset of the item's first line within ``lines``. Continuation lines (non-blank,
    not starting a new ``N.``) are appended to the current item until the next numbered line, so a
    citation that wraps onto its own line is still part of the objective text.
    """
    number_re = re.compile(r"^(\d+)\.\s+")
    items = []
    current = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = number_re.match(stripped)
        if match:
            current = {"num": int(match.group(1)), "text": stripped, "line_index": i}
            items.append(current)
        elif current is not None and stripped:
            current["text"] += " " + stripped
    return items


# Objective citation patterns (Section 1.3): (AC: #N — text) and (NFR: category — text).
CITATION_RE = re.compile(r"\((?:AC|NFR):\s*")
_AC_NUM_RE = re.compile(r"\(AC:\s*#(\d+)")
_NFR_CAT_RE = re.compile(r"\(NFR:\s*(.+?)\s*(?:—|\))")


def has_citation(text: str) -> bool:
    """True if the objective text carries an ``(AC: ...)`` or ``(NFR: ...)`` citation marker."""
    return bool(CITATION_RE.search(text))


def parse_citation(text: str) -> dict | None:
    """Extract the AC/NFR citation from an objective line.

    Returns ``{"kind": "AC"|"NFR", "number": int|None, "category": str|None}`` or ``None`` when
    no citation marker is present. ``number`` is the parsed ``#N`` for AC citations (``None`` when
    absent); ``category`` is the text between ``NFR:`` and the em-dash for NFR citations. Applying
    count/category bounds to these fields is the caller's policy, not this parser's job.
    """
    if not CITATION_RE.search(text):
        return None
    if "(AC:" in text:
        match = _AC_NUM_RE.search(text)
        return {"kind": "AC", "number": int(match.group(1)) if match else None, "category": None}
    match = _NFR_CAT_RE.search(text)
    return {"kind": "NFR", "number": None, "category": match.group(1).strip() if match else ""}


def normalize_interface(name: str) -> str:
    """Normalize an interface/table-cell name for tolerant matching across sections.

    Sections are independently LLM-authored, so the same name can appear with or without
    backticks or bold, or with trailing punctuation. Strip that formatting and casefold so
    cosmetic drift is not reported as a mismatch.
    """
    cleaned = name.replace("`", "").replace("*", "").strip()
    return cleaned.rstrip(".,;:").strip().casefold()
