"""Utilities for parsing sections from fetched STRAT content (Jira wiki markup).

Extracts structured data from the output of fetch_issue.py, which preserves
Jira wiki markup (h2., h3., *bold*, {{code}}) inside the Description section.
"""

import re

_TESTABILITY_HEADING_RE = re.compile(r"^h3\.\s+Testability(:.*)?\s*$")


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


def _extract_bulleted_texts(section: str) -> list[str]:
    """Split a Jira wiki section body into merged, whitespace-normalized bullet-item strings.

    Handles both `#` (numbered) and `*` (plain) bullet markers, and falls back to blank-line
    paragraph splitting when no bullet marker is present.
    """
    stripped = section.strip()

    if re.search(r"(?m)^#\s+", stripped):
        bullet_marker = r"(?m)^#\s+"
    elif re.search(r"(?m)^\*\s+", stripped):
        bullet_marker = r"(?m)^\*\s+"
    else:
        bullet_marker = None

    if bullet_marker:
        # Split on the bullet marker directly so entries survive with no blank line between them.
        return [" ".join(item.split()) for item in re.split(bullet_marker, stripped)[1:] if item.strip()]

    merged = []
    for para in re.split(r"\n\n+", stripped):
        if text := " ".join(para.split()):
            merged.append(text)
    return merged


def parse_acceptance_criteria(content: str) -> dict:
    """Extract acceptance criteria from STRAT content, folding in Testability-section edge cases.

    An optional `h3. Testability` section (exact `h3. Testability` or colon-qualified e.g.
    "h3. Testability: Additional Acceptance Criteria") holds numbered edge cases in the same
    `# *Title*: Given/When/Then` shape as the main list; these continue the numbering so
    downstream consumers (ac_count, ac_json, the `(AC: #N)` gate) treat them identically.
    Headings like `h3. Testability Concerns` or `h3. Testability Notes` (without a colon) are
    ignored. The main section is mandatory — Testability is not a fallback if it's absent. Items
    whose sentence exactly duplicates (case/whitespace-insensitive) one already present are
    skipped; semantic near-duplicates are not detected.
    """
    section = extract_jira_section(content, "h3. Acceptance Criteria")
    if section is None:
        return {"found": False, "count": 0, "acceptance_criteria": []}

    texts = _extract_bulleted_texts(section)

    testability_heading = None
    for line in content.splitlines():
        if _TESTABILITY_HEADING_RE.match(line):
            testability_heading = line
            break

    testability_section = (
        extract_jira_section(content, testability_heading) if testability_heading is not None else None
    )
    if testability_section:
        seen = {" ".join(_parse_bullet_item(text)["text"].split()).casefold() for text in texts}
        for raw in _extract_bulleted_texts(testability_section):
            item = _parse_bullet_item(raw)
            sentence = item["text"]
            normalized = " ".join(sentence.split()).casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            texts.append(f"{item['title']}: {sentence}" if item["title"] else sentence)

    criteria = [{"num": i + 1, "text": t} for i, t in enumerate(texts)]
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
        elif requirements and not line.startswith("*"):
            # Merge wrapped continuation text, but not a new "*" bullet that failed nfr_re.
            requirements[-1]["text"] = f"{requirements[-1]['text']} {line}"

    return {"found": True, "requirements": requirements}


def gate_inputs(content: str) -> dict:
    """Derive the citation gate's deterministic inputs from STRAT content.

    Returns ``{"ac_count": int, "nfr_categories": [str, ...]}`` where ``ac_count`` is the
    acceptance-criteria count and ``nfr_categories`` is the order-preserving, de-duplicated list of
    NFR category names.  Downstream: ``parse_strat.py`` prints it as JSON; the shell iterates it
    with ``jq -r '.nfr_categories[]'`` and builds repeated ``--nfr-category`` flags for
    ``validate.py ac-citations``.
    """
    ac = parse_acceptance_criteria(content)
    nfr = parse_nfr(content)
    categories = list(dict.fromkeys(r["category"] for r in nfr["requirements"]))
    return {"ac_count": ac["count"], "nfr_categories": categories}


def workflow_inputs(content: str) -> dict:
    """Combine AC/NFR/out-of-scope parsing with gate_inputs for test-plan-create's Step 1.5: one
    call in place of four separate parse_strat.py subcommands plus inline jq/bash validation.

    Returns ``{"status": "no_acceptance_criteria", "ac_json": {...}}`` when the strategy has zero
    parseable acceptance criteria — a content problem the caller must handle explicitly (STOP and
    record a Rework verdict), not conflate with a parsing/execution failure. Otherwise returns
    ``{"status": "ok", "ac_json": ..., "nfr_json": ..., "oos_json": ..., "ac_count": ...,
    "nfr_categories": [...]}`` with ``nfr_json``/``oos_json`` preserving their own ``found`` flag
    (a strategy legitimately lacking either section is not an error).
    """
    ac_json = parse_acceptance_criteria(content)
    if not ac_json["found"] or ac_json["count"] == 0:
        return {"status": "no_acceptance_criteria", "ac_json": ac_json}

    inputs = gate_inputs(content)
    return {
        "status": "ok",
        "ac_json": ac_json,
        "nfr_json": parse_nfr(content),
        "oos_json": parse_out_of_scope(content),
        "ac_count": inputs["ac_count"],
        "nfr_categories": inputs["nfr_categories"],
    }


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
