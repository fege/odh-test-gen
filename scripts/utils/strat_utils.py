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

    paragraphs = re.split(r"\n\n+", section.strip())
    criteria = []
    for para in paragraphs:
        text = " ".join(para.split())
        if text:
            criteria.append({"text": text})

    return {"found": True, "count": len(criteria), "acceptance_criteria": criteria}


def parse_nfr(content: str) -> dict:
    """Extract non-functional requirements from STRAT content."""
    section = extract_jira_section(content, "h3. Non-Functional Requirements")
    if section is None:
        return {"found": False, "requirements": []}

    nfr_re = re.compile(r"^\*\s+\*([^*]+)\*:\s*(.+)", re.DOTALL)
    requirements = []
    for line in section.splitlines():
        match = nfr_re.match(line)
        if match:
            requirements.append(
                {
                    "category": match.group(1).strip(),
                    "text": match.group(2).strip(),
                }
            )

    return {"found": True, "requirements": requirements}


def parse_out_of_scope(content: str) -> dict:
    """Extract out-of-scope items from STRAT content."""
    section = extract_jira_section(content, "h3. Out-of-Scope")
    if section is None:
        return {"found": False, "count": 0, "items": []}

    item_re = re.compile(r"^\*\s+\*([^*]+)\*:\s*(.+)")
    items = []
    for line in section.splitlines():
        match = item_re.match(line)
        if match:
            items.append(
                {
                    "title": match.group(1).strip(),
                    "text": match.group(2).strip(),
                }
            )

    return {"found": True, "count": len(items), "items": items}


def generate_objective_stubs(ac_result: dict) -> list[str]:
    """Generate numbered test objective stubs from parsed acceptance criteria.

    Each stub references its AC by number. The LLM fills in [FILL] with
    the e2e/UI test objective text.
    """
    if not ac_result.get("found") or ac_result.get("count", 0) == 0:
        return []

    return [
        f"{i}. Verify [FILL] via [e2e/UI approach] (AC: #{i})"
        for i, _ in enumerate(ac_result["acceptance_criteria"], 1)
    ]
