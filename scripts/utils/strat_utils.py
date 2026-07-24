"""Utilities for parsing sections from fetched STRAT content (Jira wiki markup).

Extracts structured data from the output of fetch_issue.py, which preserves
Jira wiki markup (h2., h3., *bold*, {{code}}) inside the Description section.
"""

import re


def extract_jira_section(content: str, heading_prefix: str) -> str | None:
    """Extract text between a Jira wiki heading and the next h2./h3. heading.

    Returns the section body text, or None if heading not found.
    """
    lines = content.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(heading_prefix):
            start = i + 1
            continue
        if start is not None and re.match(r"^h[23]\.\s", line):
            return "\n".join(lines[start:i]).strip()
    if start is not None:
        return "\n".join(lines[start:]).strip()
    return None


def parse_acceptance_criteria(content: str) -> dict:
    """Extract acceptance criteria from STRAT content."""
    section = extract_jira_section(content, "h3. Acceptance Criteria")
    if section is None:
        return {"found": False, "count": 0, "acceptance_criteria": []}

    stripped = section.strip()

    if re.search(r"(?m)^#\s+", stripped):
        bullet_marker = r"(?m)^#\s+"
    elif re.search(r"(?m)^\*\s+", stripped):
        bullet_marker = r"(?m)^\*\s+"
    else:
        bullet_marker = None

    if bullet_marker:
        # Split on the bullet marker directly so entries survive with no blank line between them.
        merged = [" ".join(item.split()) for item in re.split(bullet_marker, stripped)[1:] if item.strip()]
    else:
        merged = []
        for para in re.split(r"\n\n+", stripped):
            if text := " ".join(para.split()):
                merged.append(text)

    criteria = [{"text": t} for t in merged]
    return {"found": True, "count": len(criteria), "acceptance_criteria": criteria}


def parse_nfr(content: str) -> dict:
    """Extract non-functional requirements from STRAT content."""
    section = extract_jira_section(content, "h3. Non-Functional Requirements")
    if section is None:
        return {"found": False, "requirements": []}

    nfr_re = re.compile(r"^\*\s+\*([^*]+)\*:\s*(.+)")
    requirements = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = nfr_re.match(line)
        if match:
            requirements.append(
                {
                    "category": match.group(1).strip(),
                    "text": match.group(2).strip(),
                }
            )
        elif requirements:
            requirements[-1]["text"] = f"{requirements[-1]['text']} {line}"

    return {"found": True, "requirements": requirements}


def _parse_bullet_item(text: str) -> dict:
    """Parse a single bullet item, extracting bold title if present."""
    bold_match = re.match(r"^\*([^*]+)\*\s*(.*)", text)
    if bold_match:
        title = bold_match.group(1).strip()
        rest = bold_match.group(2).strip()
        rest = rest.lstrip(":—–-").strip()
        return {"title": title, "text": rest}
    return {"title": "", "text": text}


def parse_out_of_scope(content: str) -> dict:
    """Extract out-of-scope items from STRAT content."""
    section = extract_jira_section(content, "h3. Out-of-Scope")
    if section is None:
        return {"found": False, "count": 0, "items": []}

    bullet_re = re.compile(r"^\*\s+(.+)")
    items = []
    for line in section.splitlines():
        bullet_match = bullet_re.match(line)
        if bullet_match:
            items.append(_parse_bullet_item(bullet_match.group(1).strip()))

    return {"found": True, "count": len(items), "items": items}
