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


# Objective citation patterns (Section 1.3): (AC: #N — text) and (NFR: category — text). Both
# require a dash separator (ASCII hyphen -, en dash –, or em dash —) and non-empty explanatory
# text before a closing paren — a bare (AC: #N) / (NFR: category), or a citation with no
# closing paren at all, is not recognized.
#
# Every trailing repetition quantifier is bounded to _MAX chars to prevent quadratic-time
# (ReDoS) rescanning when the regex engine backtracks on unterminated input.
_DASH = r"[-\u2013\u2014]"
_MAX = 1024  # upper bound on field-width quantifiers — prevents ReDoS backtracking

# The NFR category may itself contain an intra-word hyphen (e.g. "Multi-tenancy"). Only a dash
# with whitespace on both sides is the separator -- an unspaced hyphen is part of the category
# text, not a terminator. The AC branch has no free-text category, so this ambiguity doesn't
# apply there; its dash stays whitespace-tolerant on both sides as before.
_AC_BRANCH = r"AC:\s*(?:#\d{1,%d})?\s*" % _MAX + _DASH + r"\s*"
_NFR_BRANCH = r"NFR:\s*[^\s\-\u2013\u2014)][^)]{0,%d}?\s+" % _MAX + _DASH + r"\s+"
CITATION_RE = re.compile(r"\((?:" + _AC_BRANCH + "|" + _NFR_BRANCH + r")[^\s)][^)]{0,%d}\)" % _MAX)
_AC_CITATION_RE = re.compile(r"\(AC:\s*(?:#(\d{1,%d}))?\s*" % _MAX + _DASH + r"\s*[^\s)][^)]{0,%d}\)" % _MAX)
_NFR_CITATION_RE = re.compile(
    r"\(NFR:\s*([^\s\-\u2013\u2014)][^)]{0,%d}?)\s+" % _MAX + _DASH + r"\s+[^\s)][^)]{0,%d}\)" % _MAX
)


def has_citation(text: str) -> bool:
    """True if the objective text carries a complete ``(AC: #N — text)`` or
    ``(NFR: category — text)`` citation. A dash separator (ASCII hyphen ``-``, en dash ``–``, or
    em dash ``—``), explanatory text, and closing paren are all required — a bare
    ``(AC: #N)``/``(NFR: category)`` or an unterminated citation does not count.
    """
    return bool(CITATION_RE.search(text))


def parse_citations(text: str) -> list[dict]:
    """Extract every AC/NFR citation from an objective line, in left-to-right document order.

    Returns a list of ``{"kind": "AC"|"NFR", "number": int|None, "category": str|None}`` dicts, one
    per complete citation, and ``[]`` when none are present. A bare ``(AC: #N)``/``(NFR: category)``
    or an unterminated citation (no closing paren) is not a complete citation and never appears in
    the list. ``number`` is the parsed ``#N`` for AC citations (``None`` when the number itself is
    absent, e.g. ``(AC: — text)`` — a milder defect than missing the citation entirely);
    ``category`` is the text between ``NFR:`` and the dash separator (ASCII hyphen, en dash, or em
    dash) for NFR citations. Applying count/category bounds to these fields is the caller's policy,
    not this parser's job.
    """
    citations = []
    for citation_match in CITATION_RE.finditer(text):
        # Parse each matched citation itself, not the whole text — a bare/incomplete marker of the
        # other kind sitting elsewhere in the text must not hijack which citation gets parsed.
        matched = citation_match.group(0)
        if matched.startswith("(AC:"):
            match = _AC_CITATION_RE.search(matched)
            citations.append(
                {"kind": "AC", "number": int(match.group(1)) if match and match.group(1) else None, "category": None}
            )
        else:
            match = _NFR_CITATION_RE.search(matched)
            citations.append({"kind": "NFR", "number": None, "category": match.group(1).strip() if match else ""})
    return citations


def normalize_interface(name: str) -> str:
    """Normalize an interface/table-cell name for tolerant matching across sections.

    Sections are independently LLM-authored, so the same name can appear with or without
    backticks or bold, or with trailing punctuation. Strip that formatting and casefold so
    cosmetic drift is not reported as a mismatch.
    """
    cleaned = name.replace("`", "").replace("*", "").strip()
    return cleaned.rstrip(".,;:").strip().casefold()
