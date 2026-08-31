#!/usr/bin/env python3
"""Deterministic evidence checks used by the test-plan quality gate.

Scope coverage is intentionally based on the structured AC/NFR identifiers in Section 1.3,
not on trying to decide whether arbitrary strategy prose is semantically similar to plan prose.
Actionability checks the explicit, operational fields in Section 3.
"""

import re
from pathlib import Path

from scripts.utils.markdown_utils import extract_section, parse_citations, parse_numbered_objectives, parse_table_rows
from scripts.utils.schemas import TEMPLATE_HEADINGS
from scripts.utils.strat_utils import parse_acceptance_criteria, parse_nfr


_VERSION_LABELS = ("OpenShift version", "RHOAI version")
_TBD_RE = re.compile(r"\bTBD\b", re.IGNORECASE)
_VAGUE_VERSION_RE = re.compile(r"^(?:latest|current|the supported version|to be determined)$", re.IGNORECASE)
_FIELD_RE = re.compile(r"^\s*([^:]+):\s*(.*?)\s*$")
_OBJECTIVE_REF_RE = re.compile(r"\(Objective:\s*#(\d+)\)", re.IGNORECASE)
_NOT_APPLICABLE_RE = re.compile(r"^\*\*Not Applicable\*\*", re.IGNORECASE)
_NFR_SECTIONS = frozenset({"7.1", "7.2", "7.3", "7.4", "7.5"})
_TBD_RESOLUTION_RE = re.compile(
    r"\bTBD — Resolution:\s*"
    r"(?i:resolve|retrieve|obtain|confirm|determine|check|verify)\b.*?"
    r"\b(?P<connector>(?i:from|with|by|before|after|using))\b\s*(?P<target>[^.;\n]+)",
)
_GENERIC_RESOLUTION_TARGET_RE = re.compile(
    r"^(?:(?:the|a|an|some|any|appropriate|relevant|responsible|right|correct)\s+)*"
    r"(?:(?:test(?:ing)?|feature|product|project|development|developer|qa|qe|quality assurance)\s+)?"
    r"(?:someone|somebody|anyone|anybody|person|people|team|owner|stakeholders?|engineering|"
    r"documentation|docs?|source|information|details?)$",
    re.IGNORECASE,
)
_NAMED_SOURCE_OR_OWNER_RE = re.compile(
    r"\b(?:[\w/-]+\s+)+(?:team|engineering|owner|manager|administrator|lead|maintainer|operator)\b"
    r"|\b(?:ADR|API spec(?:ification)?|feature refinement|design doc(?:ument)?|Jira (?:issue|ticket))\b"
    r"|\b(?:[\w/-]+\s+)+(?:matrix|runbook|guide|roadmap|document|specification|release notes)\b",
    re.IGNORECASE,
)
_CONCRETE_TIMING_RE = re.compile(
    r"\b(?:before|after|by)\s+(?:the\s+)?(?:(?:end of|next)\s+)?(?:environment\s+)?"
    r"(?:setup|provisioning|test(?:ing)?(?:\s+(?:setup|execution))?|release|deployment|"
    r"kickoff|go/no-go(?:\s+decision)?|design review|sprint planning)\b",
    re.IGNORECASE,
)
_CONCRETE_PERMISSION_RE = re.compile(
    r"\b(?:create|get|list|watch|update|patch|delete|read|write|use|admin|cluster-admin)\b", re.IGNORECASE
)
_CONCRETE_PROSE_RESOURCE_RE = re.compile(
    r"\b[a-z0-9][\w.-]*\s+(?:namespaces?|projects?|service accounts?|endpoints?|apis?|crds?|models?|"
    r"stores?|pipelines?|dashboards?|resources?)\b",
    re.IGNORECASE,
)
_BROAD_PROSE_RESOURCE_RE = re.compile(
    r"\b(?:all|any|every)\s+(?:[a-z0-9][\w.-]*\s+){0,3}(?:namespaces?|projects?|service accounts?|"
    r"endpoints?|apis?|crds?|models?|stores?|pipelines?|dashboards?|resources?)\b",
    re.IGNORECASE,
)
_GENERIC_RESOURCE_VALUES = {"resource", "resources", "the resource", "all resources", "*"}


def _missing(section: str, text: str, reason: str) -> dict:
    return {"section": section, "text": text, "reason": reason}


def _objective_records(content: str) -> list[dict]:
    lines, start_line = extract_section(content, TEMPLATE_HEADINGS["1.3"])
    if not lines:
        return []
    return [
        {
            "section": "1.3",
            "number": objective["num"],
            "text": objective["text"],
            "line_number": start_line + objective["line_index"],
        }
        for objective in parse_numbered_objectives(lines)
    ]


def _scope_entries(lines: list[str], section: str) -> list[dict]:
    """Return meaningful entries from a scope-bearing section and their objective references.

    The contract intentionally requires an explicit ``(Objective: #N)`` marker. It does not try
    to derive a relationship from free-form wording. Section 8's table rows use the risk cell as
    the displayed entry while searching the whole row for the marker.
    """
    entries = []
    paragraph = []
    in_out_of_scope = False

    def add_paragraph() -> None:
        if not paragraph or in_out_of_scope:
            return
        text = " ".join(paragraph)
        entries.append({"section": section, "text": paragraph[0], "references": _OBJECTIVE_REF_RE.findall(text)})

    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            add_paragraph()
            paragraph = []
            table_lines = []
            while index < len(lines):
                candidate = lines[index].strip()
                if not (candidate.startswith("|") and candidate.endswith("|")):
                    break
                table_lines.append(candidate)
                index += 1
            rows = parse_table_rows(table_lines)
            for row in rows:
                if row and not in_out_of_scope:
                    entries.append(
                        {"section": section, "text": row[0], "references": _OBJECTIVE_REF_RE.findall(" | ".join(row))}
                    )
            continue
        if not stripped:
            add_paragraph()
            paragraph = []
        elif stripped.startswith("#"):
            add_paragraph()
            paragraph = []
            in_out_of_scope = section == "1.2" and "out of scope" in stripped.casefold()
        elif re.fullmatch(r"-{3,}", stripped):
            add_paragraph()
            paragraph = []
        elif re.match(r"^\d+\.\s+", stripped):
            add_paragraph()
            paragraph = [re.sub(r"^\d+\.\s+", "", stripped)]
        elif re.match(r"^[-*+]\s+", stripped):
            add_paragraph()
            paragraph = [re.sub(r"^[-*+]\s+", "", stripped)]
        else:
            paragraph.append(stripped)
        index += 1
    add_paragraph()
    return entries


def _scope_records(content: str) -> list[dict]:
    records = []
    for section in ("1.2", "2.3", "7.1", "7.2", "7.3", "7.4", "7.5", "8"):
        _, lines = _section_text(content, section)
        records.extend(_scope_entries(lines, section))
    return records


def validate_scope_coverage(testplan_path: str, strategy_content: str) -> dict:
    """Check both directions of the structured strategy-requirement/objective mapping.

    A strategy requirement is covered only when a Section 1.3 objective cites its AC number or
    NFR category. Conversely, every recognized citation in an objective must resolve to a real
    requirement. This deliberately does not compare arbitrary prose from Sections 1.2, 2.3, 7.x,
    or 8 with Jira text: that would produce unreliable false matches for STRAT-specific language.
    """
    path = Path(testplan_path)
    if not path.exists():
        return {
            "valid": False,
            "missing": [_missing("1.3", "TestPlan.md", "test plan is missing")],
            "unmapped_objectives": [],
        }

    ac_requirements = parse_acceptance_criteria(strategy_content)["acceptance_criteria"]
    nfr_requirements = parse_nfr(strategy_content)["requirements"]
    requirements = {
        ("AC", requirement["num"]): f"AC #{requirement['num']} — {requirement['text']}"
        for requirement in ac_requirements
    }
    requirements.update(
        {
            ("NFR", requirement["category"].casefold()): f"NFR: {requirement['category']} — {requirement['text']}"
            for requirement in nfr_requirements
        }
    )

    content = path.read_text()
    objectives = _objective_records(content)
    objective_numbers = {objective["number"] for objective in objectives}
    cited_keys: set[tuple[str, int | str]] = set()
    unmapped_objectives = []
    for objective in objectives:
        citations = parse_citations(objective["text"])
        if not citations:
            unmapped_objectives.append(_missing("1.3", objective["text"], "no grounded strategy requirement"))
            continue
        unresolved = []
        for citation in citations:
            if citation["kind"] == "AC":
                key = ("AC", citation["number"])
            else:
                key = ("NFR", (citation["category"] or "").casefold())
            if key not in requirements:
                unresolved.append(citation)
            else:
                cited_keys.add(key)
        if unresolved:
            unmapped_objectives.append(
                _missing("1.3", objective["text"], "citation does not resolve to a strategy requirement")
            )

    missing = []
    for key, requirement_text in requirements.items():
        if key not in cited_keys:
            missing.append(_missing("1.3", requirement_text, "no Section 1.3 objective"))

    for scope_entry in _scope_records(content):
        if not scope_entry["references"]:
            is_ungrounded_not_applicable = scope_entry["section"] in _NFR_SECTIONS and _NOT_APPLICABLE_RE.match(
                scope_entry["text"]
            )
            if is_ungrounded_not_applicable:
                continue
            missing.append(_missing(scope_entry["section"], scope_entry["text"], "no Section 1.3 objective mapping"))
            continue
        for reference in scope_entry["references"]:
            if int(reference) not in objective_numbers:
                missing.append(
                    _missing(
                        scope_entry["section"],
                        scope_entry["text"],
                        f"Objective #{reference} does not exist in Section 1.3",
                    )
                )

    return {
        "valid": not missing and not unmapped_objectives,
        "missing": missing,
        "unmapped_objectives": unmapped_objectives,
    }


def _section_text(content: str, section: str) -> tuple[str, list[str]]:
    lines, _ = extract_section(content, TEMPLATE_HEADINGS[section])
    return "\n".join(lines).strip(), lines


def _is_placeholder(text: str) -> bool:
    # Remove Markdown blockquote prefixes without discarding a closing angle bracket from a
    # delimited value such as ``<sample payload>``.
    normalized = re.sub(r"(?m)^\s*>\s?", "", text)
    normalized = re.sub(r"[*_`]", "", normalized).strip().casefold()
    if len(normalized) >= 2 and normalized[0] + normalized[-1] in {"[]", "<>", "{}", "()"}:
        normalized = normalized[1:-1].strip()
    return (
        not normalized
        or normalized in {"tbd", "n/a", "not applicable", "-"}
        or "{what" in normalized
        or bool(
            re.fullmatch(r"(?:sample|example|placeholder|test[ -]?data)(?:[ -]?(?:payload|data|value))?", normalized)
        )
    )


def _has_tbd_resolution_path(value: str) -> bool:
    """Require a concrete, identifiable resolution path for a ``TBD`` value.

    The canonical ``TBD — Resolution:`` label requires a concrete action plus either a named
    source/owner or a concrete timing/decision point. This deliberately rejects label-less
    rationales and generic placeholders such as ``with someone`` so they cannot make an
    otherwise unknown environment version actionable.
    """
    if _is_placeholder(value):
        return False

    for match in _TBD_RESOLUTION_RE.finditer(value):
        target = match.group("target").strip(" \t:;-—–,()")
        if _CONCRETE_TIMING_RE.search(f"{match.group('connector')} {target}"):
            return True

        source_or_owner = re.split(r"\b(?:by|before|after)\b", target, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if not _GENERIC_RESOLUTION_TARGET_RE.fullmatch(source_or_owner) and _NAMED_SOURCE_OR_OWNER_RE.search(
            source_or_owner
        ):
            return True
    return False


def _version_evidence(section_text: str) -> tuple[list[str], list[str]]:
    bare_tbd = []
    missing_details = []
    lines = section_text.splitlines()
    fields = {}
    for index, line in enumerate(lines):
        match = _FIELD_RE.match(re.sub(r"[*_`]", "", re.sub(r"^\s*[-*]\s+", "", line)))
        if match:
            fields[match.group(1).strip().casefold()] = (index, match.group(2).strip())

    for label in _VERSION_LABELS:
        field = fields.get(label.casefold())
        if field is None:
            missing_details.append(label)
            continue
        index, value = field
        if not value:
            missing_details.append(label)
            continue
        tbd = _TBD_RE.search(value)
        if tbd:
            # A canonical resolution path can wrap after its action; stop at the next labelled
            # field so the following environment value cannot justify this TBD.
            continuation = []
            for next_line in lines[index + 1 :]:
                normalized_line = re.sub(r"[*_]", "", re.sub(r"^\s*[-*]\s+", "", next_line))
                if _FIELD_RE.match(normalized_line):
                    break
                if next_line.strip():
                    continuation.append(next_line.strip())
            resolution_value = " ".join([value, *continuation]).strip()
            if not _has_tbd_resolution_path(resolution_value):
                bare_tbd.append(label)
        elif _VAGUE_VERSION_RE.fullmatch(value.strip()):
            missing_details.append(label)
        elif _is_placeholder(value):
            missing_details.append(label)

    return bare_tbd, missing_details


def _actionability_for_test_data(section_text: str) -> bool:
    if _is_placeholder(section_text):
        return False
    has_format = bool(re.search(r"\b(?:json|yaml|xml|csv|payload|schema|object|record|field)\b", section_text, re.I))
    examples = re.findall(r"\{[^{}\n]+\}|\[[^\[\]\n]+\]|<[^<>\n]+>", section_text)
    examples.extend(
        match.group(1)
        for match in re.finditer(
            r"\b(?:example|e\.g\.|sample|fixture)\b\s*(?::|=|is|such as|[-—])?\s*([^;\n|]+)",
            section_text,
            re.I,
        )
    )
    has_example = any(not _is_placeholder(example) and not _TBD_RE.search(example) for example in examples)
    return has_format and has_example


def _actionability_for_users(section_text: str, lines: list[str]) -> bool:
    if _is_placeholder(section_text):
        return False
    if re.search(r"\bnot applicable\b", section_text, re.I):
        return len(section_text.split()) > 3
    table_has_rbac = False
    for index, line in enumerate(lines):
        header = line.strip()
        if not (header.startswith("|") and header.endswith("|")):
            continue
        headers = [cell.strip().casefold() for cell in header.strip("|").split("|")]
        role_columns = [
            i for i, cell in enumerate(headers) if any(name in cell for name in ("role", "user", "account"))
        ]
        permission_columns = [i for i, cell in enumerate(headers) if "permission" in cell]
        resource_columns = [
            i for i, cell in enumerate(headers) if any(name in cell for name in ("resource", "namespace", "project"))
        ]
        rows = parse_table_rows(lines[index:])
        for row in rows:
            if (
                role_columns
                and permission_columns
                and resource_columns
                and max(role_columns + permission_columns + resource_columns) < len(row)
                and not _is_placeholder(row[role_columns[0]])
                and _is_concrete_resource(row[resource_columns[0]])
                and _CONCRETE_PERMISSION_RE.search(row[permission_columns[0]])
            ):
                table_has_rbac = True
                break
        if table_has_rbac:
            break
    prose_has_rbac = bool(
        re.search(r"\b(?:role|user|service account)\b", section_text, re.I)
        and _CONCRETE_PERMISSION_RE.search(section_text)
        and _has_concrete_prose_resource(section_text)
        and re.search(r"\b(?:can|may|allowed|permission)\b", section_text, re.I)
    )
    return table_has_rbac or prose_has_rbac


def _is_concrete_resource(value: str) -> bool:
    normalized = value.strip().casefold()
    return not _is_placeholder(value) and normalized not in _GENERIC_RESOURCE_VALUES


def _has_concrete_prose_resource(value: str) -> bool:
    """Require a named resource kind and reject broad resource collections in prose RBAC."""
    return not _BROAD_PROSE_RESOURCE_RE.search(value) and bool(_CONCRETE_PROSE_RESOURCE_RE.search(value))


def validate_actionability(testplan_path: str) -> dict:
    """Check the minimum operational evidence required for an Actionability 2/2 score."""
    path = Path(testplan_path)
    if not path.exists():
        return {
            "valid": False,
            "bare_tbd": [],
            "missing_details": [
                "environment versions and configuration",
                "test data formats and examples",
                "RBAC roles and permissions",
            ],
        }

    content = path.read_text()
    infra_text, _ = _section_text(content, "3.1")
    data_text, _ = _section_text(content, "3.2")
    users_text, users_lines = _section_text(content, "3.3")

    bare_tbd, missing_details = _version_evidence(infra_text)
    if not infra_text:
        missing_details.append("environment versions and configuration")
    if not _actionability_for_test_data(data_text):
        missing_details.append("test data formats and examples")
    if not _actionability_for_users(users_text, users_lines):
        missing_details.append("RBAC roles and permissions")

    # Preserve order while avoiding duplicate diagnostics when a section is both absent and
    # missing a specific field.
    missing_details = list(dict.fromkeys(missing_details))
    return {
        "valid": not bare_tbd and not missing_details,
        "bare_tbd": bare_tbd,
        "missing_details": missing_details,
    }
