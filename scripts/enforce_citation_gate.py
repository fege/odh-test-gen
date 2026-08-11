#!/usr/bin/env python3
"""Force-correct Scope Fidelity when the review agent disagrees with the deterministic citation
checks it was given.

score-agent.md instructs the LLM to read ac_citations_result.valid / ac_coverage_result.valid
directly and cap Scope Fidelity to <= 1 when either is false — but LLM compliance with that
instruction isn't guaranteed. This re-applies that same rule after TestPlanReview.md is written:
overriding the recorded score when it's inconsistent with the already-computed result, and
injecting a deterministic feedback note (which objectives are uncited/invalid, which AC numbers
are missing) so the revise agent has something concrete to act on even if the review agent's own
prose feedback missed the problem.

Usage:
    python3 scripts/enforce_citation_gate.py <feature_dir> \
        --ac-citations-result '<json from validate.py ac-citations>' \
        --ac-coverage-result '<json from validate.py ac-coverage>'

Exit code 0 always; prints a JSON object to stdout with `status` one of "overridden", "ok",
"skip", or "error" (with an `error` message field).
"""

import argparse
import json
import os
import sys
import yaml


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


def _build_feedback_note(ac_citations_result: dict, ac_coverage_result: dict) -> str:
    lines = [
        "**Automated correction (deterministic citation gate)**: Scope Fidelity was capped to "
        "1/2 — the recorded score did not reflect this.",
    ]
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
    lines.append(
        "\nFix: add a machine-checkable `(AC: #N — short description)` or "
        "`(NFR: category — text)` citation to each listed objective."
    )
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


def cap_scope_fidelity(scores: dict, ac_citations_result: dict, ac_coverage_result: dict) -> dict:
    """Cap Scope Fidelity to 1 if the deterministic citation checks say it should be, but
    `scores` says 2. Pure — no file I/O — shared by enforce_citation_gate() (which persists the
    result to TestPlanReview.md) and test-plan-score (which has no review file and only needs
    the corrected numbers to present).
    """
    _validate_scores(scores)
    _require_valid_field(ac_citations_result, "ac_citations_result")
    _require_valid_field(ac_coverage_result, "ac_coverage_result")

    citations_ok = ac_citations_result["valid"] and ac_coverage_result["valid"]
    scores = dict(scores)
    if citations_ok or scores.get("scope_fidelity", 0) <= 1:
        return {"overridden": False, "scores": scores}

    scores["scope_fidelity"] = 1
    verdict, score, passed = compute_verdict_and_pass(scores)
    return {"overridden": True, "scores": scores, "score": score, "pass": passed, "verdict": verdict}


def enforce_citation_gate(feature_dir: str, ac_citations_result: dict, ac_coverage_result: dict) -> dict | None:
    """Cap Scope Fidelity to 1 if the deterministic citation checks say it should be, but the
    persisted review score says 2. Returns None if TestPlanReview.md doesn't exist.
    """
    _require_valid_field(ac_citations_result, "ac_citations_result")
    _require_valid_field(ac_coverage_result, "ac_coverage_result")

    review_path = os.path.join(feature_dir, "TestPlanReview.md")
    if not os.path.exists(review_path):
        return None

    data, _ = read_frontmatter_validated(review_path, "test-plan-review")
    old_score = data.get("score")

    result = cap_scope_fidelity(data.get("scores", {}), ac_citations_result, ac_coverage_result)
    if not result["overridden"]:
        return {"overridden": False}

    scores, score, passed, verdict = result["scores"], result["score"], result["pass"], result["verdict"]
    updates = {"scores": scores, "score": score, "pass": passed, "verdict": verdict}

    # Built before update_frontmatter runs, deliberately: if this raises on a malformed result
    # that somehow slipped past _require_valid_field, the frontmatter must not already be
    # written — a half-applied override (corrected score, no explanatory note) is worse than no
    # override at all.
    note = _build_feedback_note(ac_citations_result, ac_coverage_result)

    # A first-pass review sets before_score/before_scores equal to score not a genuine prior-cycle baseline.
    # Left uncorrected, the lowered score would look like a regression to filter_for_revision.py and get skipped.
    if data.get("before_score") == old_score:
        updates["before_score"] = score
        before_scores = dict(data.get("before_scores") or {})
        if before_scores:
            before_scores["scope_fidelity"] = 1
            updates["before_scores"] = before_scores

    update_frontmatter(review_path, updates, "test-plan-review")
    _insert_feedback_note(review_path, note)

    return {"overridden": True, "scores": scores, "score": score, "pass": passed, "verdict": verdict}


def _fail(message: str) -> None:
    """Report a machine-readable error on stdout (for the calling skill) and a matching
    diagnostic on stderr (for a human watching logs), then exit 0 — a broken gate must not abort
    the review run, but it must never look like a clean OK/SKIP/overridden result either.
    """
    print(f"enforce_citation_gate: {message}", file=sys.stderr)
    print(json.dumps({"status": "error", "error": message}))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_dir")
    parser.add_argument("--ac-citations-result", required=True, help="JSON from validate.py ac-citations")
    parser.add_argument("--ac-coverage-result", required=True, help="JSON from validate.py ac-coverage")
    try:
        args = parser.parse_args()
    except SystemExit as exc:
        if exc.code == 0:
            raise
        _fail("missing or invalid arguments")

    try:
        ac_citations = json.loads(args.ac_citations_result)
    except json.JSONDecodeError as exc:
        _fail(f"malformed --ac-citations-result JSON: {exc}")
    try:
        _require_valid_field(ac_citations, "--ac-citations-result")
    except ValueError as exc:
        _fail(str(exc))

    try:
        ac_coverage = json.loads(args.ac_coverage_result)
    except json.JSONDecodeError as exc:
        _fail(f"malformed --ac-coverage-result JSON: {exc}")
    try:
        _require_valid_field(ac_coverage, "--ac-coverage-result")
    except ValueError as exc:
        _fail(str(exc))

    try:
        result = enforce_citation_gate(args.feature_dir, ac_citations, ac_coverage)
    except (ValidationError, OSError, yaml.YAMLError, ValueError) as exc:
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
