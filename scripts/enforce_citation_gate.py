#!/usr/bin/env python3
"""Force-correct Scope Fidelity and Specificity when the review agent disagrees with the
deterministic checks it was given.

score-agent.md instructs the LLM to read ac_citations_result.valid / ac_coverage_result.valid /
scope_check_result.valid directly and cap Scope Fidelity to <= 1 when any is false, and to cap
Specificity per boilerplate_result.total_violations — but LLM compliance with those instructions
isn't guaranteed. This re-applies the same rules after TestPlanReview.md is written: overriding
the recorded score when it's inconsistent with the already-computed results, and injecting a
deterministic feedback note (which objectives are uncited/invalid, which AC numbers are missing,
which Section 2.1 levels are disallowed, which sections have boilerplate language) so the revise
agent has something concrete to act on even if the review agent's own prose feedback missed it.

Usage:
    python3 scripts/enforce_citation_gate.py <feature_dir> \
        --ac-citations-result '<json from validate.py ac-citations>' \
        --ac-coverage-result '<json from validate.py ac-coverage>' \
        --scope-check-result '<json from validate_test_scope.py>' \
        --boilerplate-result '<json from detect_boilerplate.py>'

Exit code 0 always; prints a JSON object to stdout with `status` one of "overridden", "ok",
"skip", or "error" (with an `error` message field).
"""

import argparse
import json
import os
import sys

import yaml

from scripts.utils.error_utils import exit_graceful
from scripts.utils.frontmatter_utils import read_frontmatter_validated, update_frontmatter
from scripts.utils.schemas import REVIEW_CRITERIA, ValidationError, compute_verdict_and_pass

FEEDBACK_HEADING = "## Section-by-Section Feedback"


def _require_valid_field(result, name: str) -> None:
    """Fail closed: reject anything that isn't a dict with a boolean `valid` field, and — for
    the entry lists _build_feedback_note iterates and indexes directly — reject any entry that
    isn't shaped the way it expects. A wrong-typed `valid` (e.g. the string "false", which Python
    truthiness alone would treat as truthy) or a malformed entry (e.g. `null` inside `uncited`)
    must never be silently accepted: the latter would otherwise raise mid-write, after
    TestPlanReview.md's frontmatter has already been updated but before the feedback note
    explaining why is inserted.
    """
    if not isinstance(result, dict):
        raise ValueError(f"{name} must be a JSON object")
    if not isinstance(result.get("valid"), bool):
        raise ValueError(f"{name} must have a boolean 'valid' field")

    entry_requirements = (
        ("uncited", ("text", "line_number")),
        ("invalid_citations", ("text", "line_number", "reasons")),
        ("violations", ("line", "matched_pattern", "context")),
    )
    for key, required_fields in entry_requirements:
        entries = result.get(key)
        if entries is None:
            continue
        if not isinstance(entries, list):
            raise ValueError(f"{name}.{key} must be a list")
        for entry in entries:
            if not isinstance(entry, dict) or not all(field in entry for field in required_fields):
                raise ValueError(f"{name}.{key} entries must be objects with {', '.join(required_fields)}")
        if key == "invalid_citations":
            if any(not isinstance(entry["reasons"], list) for entry in entries):
                raise ValueError(f"{name}.{key} entries must have a list 'reasons' field")
            if any(not isinstance(r, str) for entry in entries for r in entry["reasons"]):
                raise ValueError(f"{name}.{key} entries must have a list of string 'reasons'")

    # boilerplate_result.by_section is section_id -> [entry, ...], not a flat list, so it can't
    # reuse the entry_requirements loop above — same required fields as "violations" though.
    by_section = result.get("by_section")
    if by_section is not None:
        if not isinstance(by_section, dict):
            raise ValueError(f"{name}.by_section must be an object")
        for section, entries in by_section.items():
            if not isinstance(entries, list):
                raise ValueError(f"{name}.by_section.{section} must be a list")
            for entry in entries:
                if not isinstance(entry, dict) or not all(
                    field in entry for field in ("line", "matched_pattern", "context")
                ):
                    raise ValueError(
                        f"{name}.by_section.{section} entries must be objects with line, matched_pattern, context"
                    )


def _build_feedback_note(
    ac_citations_result: dict,
    ac_coverage_result: dict,
    scope_check_result: dict,
    boilerplate_result: dict,
    scope_fidelity_capped: bool,
    specificity_capped: bool,
) -> str:
    lines: list[str] = []

    if scope_fidelity_capped:
        lines.append(
            "**Automated correction (deterministic citation/scope gate)**: Scope Fidelity was "
            "capped to 1/2 — the recorded score did not reflect this."
        )
        uncited = ac_citations_result.get("uncited") or []
        invalid = ac_citations_result.get("invalid_citations") or []
        if uncited:
            lines.append("\nObjectives with no citation at all:")
            lines.extend(f"- Line {o['line_number']}: {o['text']}" for o in uncited)
        if invalid:
            lines.append("\nObjectives with an invalid citation:")
            lines.extend(f"- Line {o['line_number']}: {o['text']} — {', '.join(o['reasons'])}" for o in invalid)
        missing = ac_coverage_result.get("missing") or []
        if missing:
            lines.append(f"\nAC numbers with no citing objective at all: {missing}")
        violations = scope_check_result.get("violations") or []
        if violations:
            lines.append("\nSection 2.1 test level issues:")
            lines.extend(f"- Line {v['line']}: {v['matched_pattern']} ({v['context']})" for v in violations)
        lines.append(
            "\nFix: add a machine-checkable `(AC: #N — short description)` or "
            "`(NFR: category — text)` citation to each listed objective, and/or remove the "
            "disallowed test levels/patterns from Section 2.1."
        )

    if specificity_capped:
        if lines:
            lines.append("\n---")
        lines.append(
            "**Automated correction (deterministic boilerplate gate)**: Specificity was capped "
            "— the recorded score did not reflect this."
        )
        for section, violations in (boilerplate_result.get("by_section") or {}).items():
            lines.append(f"\nSection {section} generic phrases:")
            lines.extend(f"- Line {v['line']}: {v['matched_pattern']} ({v['context']})" for v in violations)
        lines.append("\nFix: replace generic phrasing in Sections 1.3/2.3/8 with feature-specific language.")

    return "\n".join(lines)


def _insert_feedback_note(review_path: str, note: str) -> None:
    with open(review_path, encoding="utf-8") as f:
        content = f.read()

    idx = content.find(FEEDBACK_HEADING)
    if idx == -1:
        return  # body doesn't match expected shape — frontmatter override still applies

    insert_at = idx + len(FEEDBACK_HEADING)
    content = content[:insert_at] + "\n\n" + note + content[insert_at:]

    with open(review_path, "w", encoding="utf-8") as f:
        f.write(content)


def _validate_scores(scores: dict) -> None:
    """Reject anything that isn't a dict containing exactly the 5 rubric criteria, with each
    value being an integer in range 0..2 inclusive (rejecting boolean values explicitly).
    """
    if not isinstance(scores, dict):
        raise ValueError("scores must be a JSON object")

    expected = set(REVIEW_CRITERIA)
    actual = set(scores.keys())

    missing = expected - actual
    if missing:
        raise ValueError(f"scores is missing required criteria: {', '.join(sorted(missing))}")

    extra = actual - expected
    if extra:
        raise ValueError(f"scores contains unknown criteria: {', '.join(sorted(extra))}")

    for k in REVIEW_CRITERIA:
        v = scores[k]
        if type(v) is not int:
            raise ValueError(f"scores.{k} must be an integer, got {type(v).__name__}")
        if not (0 <= v <= 2):
            raise ValueError(f"scores.{k} must be between 0 and 2, got {v}")


def _raise_if_script_error(result: dict) -> None:
    """Script/config failures return {valid: false, error: "..."} — surface that message, not a
    missing-field story that main() used to wrap as invalid TestPlanReview.md.
    """
    error = result.get("error")
    if isinstance(error, str):
        raise ValueError(error)


def _validate_scope_for_capping(result: dict, name: str) -> None:
    """Require a violations list on scope_check_result used for score capping (may be empty)."""
    _raise_if_script_error(result)
    if "violations" not in result:
        raise ValueError(f"{name} must have a 'violations' list")
    if not isinstance(result["violations"], list):
        raise ValueError(f"{name}.violations must be a list")


def _validate_boilerplate_for_capping(result: dict, name: str) -> None:
    """Require integer total_violations on boilerplate_result used for score capping."""
    _raise_if_script_error(result)
    total = result.get("total_violations")
    if not isinstance(total, int) or isinstance(total, bool):
        raise ValueError(f"{name}.total_violations must be an integer")


def cap_scope_fidelity(
    scores: dict, ac_citations_result: dict, ac_coverage_result: dict, scope_check_result: dict
) -> dict:
    """Cap Scope Fidelity to 1 if the deterministic citation/coverage/scope checks say it
    should be, but `scores` says 2. Pure — no file I/O — shared by enforce_citation_gate() (which
    persists the result to TestPlanReview.md) and test-plan-score (which has no review file and
    only needs the corrected numbers to present).
    """
    _validate_scores(scores)
    _require_valid_field(ac_citations_result, "ac_citations_result")
    _require_valid_field(ac_coverage_result, "ac_coverage_result")
    _require_valid_field(scope_check_result, "scope_check_result")
    _validate_scope_for_capping(scope_check_result, "scope_check_result")

    scope_ok = ac_citations_result["valid"] and ac_coverage_result["valid"] and scope_check_result["valid"]
    scores = dict(scores)
    if scope_ok or scores.get("scope_fidelity", 0) <= 1:
        return {"overridden": False, "scores": scores}

    scores["scope_fidelity"] = 1
    verdict, score, passed = compute_verdict_and_pass(scores)
    return {"overridden": True, "scores": scores, "score": score, "pass": passed, "verdict": verdict}


def cap_specificity(scores: dict, boilerplate_result: dict) -> dict:
    """Cap Specificity per score-agent.md's boilerplate severity tiers (>=5 violations -> 0,
    >=3 -> 1), but `scores` disagrees. Pure — no file I/O — same shape as cap_scope_fidelity,
    shared by enforce_citation_gate() and test-plan-score for the same reason.
    """
    _validate_scores(scores)
    _require_valid_field(boilerplate_result, "boilerplate_result")
    _validate_boilerplate_for_capping(boilerplate_result, "boilerplate_result")
    total = boilerplate_result["total_violations"]

    cap = 0 if total >= 5 else (1 if total >= 3 else None)
    scores = dict(scores)
    if cap is None or scores.get("specificity", 0) <= cap:
        return {"overridden": False, "scores": scores}

    scores["specificity"] = cap
    verdict, score, passed = compute_verdict_and_pass(scores)
    return {"overridden": True, "scores": scores, "score": score, "pass": passed, "verdict": verdict}


def apply_score_caps(
    scores: dict,
    ac_citations_result: dict,
    ac_coverage_result: dict,
    scope_check_result: dict,
    boilerplate_result: dict,
) -> dict:
    """Apply the Scope Fidelity and Specificity caps together and return one combined result.

    Specificity is capped against the *post-Scope-Fidelity* scores dict (not the original), so
    if both criteria need correcting, the final score/verdict/pass reflect both — not just
    whichever cap ran last with its own isolated view of `scores`.
    """
    scope_result = cap_scope_fidelity(scores, ac_citations_result, ac_coverage_result, scope_check_result)
    specificity_result = cap_specificity(scope_result["scores"], boilerplate_result)

    scope_fidelity_capped = scope_result["overridden"]
    specificity_capped = specificity_result["overridden"]
    if not scope_fidelity_capped and not specificity_capped:
        return {"overridden": False, "scores": specificity_result["scores"]}

    final = specificity_result if specificity_capped else scope_result
    return {
        "overridden": True,
        "scores": final["scores"],
        "score": final["score"],
        "pass": final["pass"],
        "verdict": final["verdict"],
        "scope_fidelity_capped": scope_fidelity_capped,
        "specificity_capped": specificity_capped,
    }


def enforce_citation_gate(
    feature_dir: str,
    ac_citations_result: dict,
    ac_coverage_result: dict,
    scope_check_result: dict,
    boilerplate_result: dict,
) -> dict | None:
    """Cap Scope Fidelity/Specificity if the deterministic checks say they should be, but the
    persisted review scores disagree. Returns None if TestPlanReview.md doesn't exist.
    """
    _require_valid_field(ac_citations_result, "ac_citations_result")
    _require_valid_field(ac_coverage_result, "ac_coverage_result")
    _require_valid_field(scope_check_result, "scope_check_result")
    _require_valid_field(boilerplate_result, "boilerplate_result")

    review_path = os.path.join(feature_dir, "TestPlanReview.md")
    if not os.path.exists(review_path):
        return None

    data, _ = read_frontmatter_validated(review_path, "test-plan-review")
    old_score = data.get("score")

    result = apply_score_caps(
        data.get("scores", {}), ac_citations_result, ac_coverage_result, scope_check_result, boilerplate_result
    )
    if not result["overridden"]:
        return {"overridden": False}

    scores, score, passed, verdict = result["scores"], result["score"], result["pass"], result["verdict"]
    scope_fidelity_capped, specificity_capped = result["scope_fidelity_capped"], result["specificity_capped"]
    updates = {"scores": scores, "score": score, "pass": passed, "verdict": verdict}

    # Built before update_frontmatter runs, deliberately: if this raises on a malformed result
    # that somehow slipped past _require_valid_field, the frontmatter must not already be
    # written — a half-applied override (corrected score, no explanatory note) is worse than no
    # override at all.
    note = _build_feedback_note(
        ac_citations_result,
        ac_coverage_result,
        scope_check_result,
        boilerplate_result,
        scope_fidelity_capped,
        specificity_capped,
    )

    # A first-pass review sets before_score/before_scores equal to score not a genuine prior-cycle baseline.
    # Left uncorrected, the lowered score would look like a regression to filter_for_revision.py and get skipped.
    if data.get("before_score") == old_score:
        updates["before_score"] = score
        before_scores = dict(data.get("before_scores") or {})
        if before_scores:
            if scope_fidelity_capped:
                before_scores["scope_fidelity"] = scores["scope_fidelity"]
            if specificity_capped:
                before_scores["specificity"] = scores["specificity"]
            updates["before_scores"] = before_scores

    update_frontmatter(review_path, updates, "test-plan-review")
    _insert_feedback_note(review_path, note)

    return {"overridden": True, "scores": scores, "score": score, "pass": passed, "verdict": verdict}


def _fail(message: str) -> None:
    """Report a machine-readable error on stdout (for the calling skill) and a matching
    diagnostic on stderr (for a human watching logs), then exit — a broken gate must not abort
    the review run, but it must never look like a clean OK/SKIP/overridden result either.
    """
    print(json.dumps({"status": "error", "error": message}))
    exit_graceful(f"enforce_citation_gate: {message}")


def _load_and_validate(raw: str, flag: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        _fail(f"malformed {flag} JSON: {exc}")
    try:
        _require_valid_field(value, flag)
    except ValueError as exc:
        _fail(str(exc))
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_dir")
    parser.add_argument("--ac-citations-result", required=True, help="JSON from validate.py ac-citations")
    parser.add_argument("--ac-coverage-result", required=True, help="JSON from validate.py ac-coverage")
    parser.add_argument("--scope-check-result", required=True, help="JSON from validate_test_scope.py")
    parser.add_argument("--boilerplate-result", required=True, help="JSON from detect_boilerplate.py")
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        if exc.code == 0:
            raise
        _fail("missing or invalid arguments")

    ac_citations = _load_and_validate(args.ac_citations_result, "--ac-citations-result")
    ac_coverage = _load_and_validate(args.ac_coverage_result, "--ac-coverage-result")
    scope_check = _load_and_validate(args.scope_check_result, "--scope-check-result")
    boilerplate = _load_and_validate(args.boilerplate_result, "--boilerplate-result")

    try:
        result = enforce_citation_gate(args.feature_dir, ac_citations, ac_coverage, scope_check, boilerplate)
    except ValueError as exc:
        _fail(str(exc))
    except (ValidationError, OSError, yaml.YAMLError) as exc:
        _fail(f"invalid TestPlanReview.md: {exc}")

    if result is None:
        print(json.dumps({"status": "skip"}))
    elif result["overridden"]:
        payload = {"status": "overridden"}
        payload.update({k: v for k, v in result.items() if k != "overridden"})
        print(json.dumps(payload))
    else:
        print(json.dumps({"status": "ok"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
