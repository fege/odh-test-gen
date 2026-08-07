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
        [--ac-coverage-result '<json from validate.py ac-coverage>']

Exit code 0 always; prints OVERRIDDEN, OK, or SKIP to stdout.
"""

import argparse
import json
import os
import sys
import yaml


from scripts.utils.frontmatter_utils import read_frontmatter_validated, update_frontmatter
from scripts.utils.schemas import ValidationError, compute_verdict_and_pass

FEEDBACK_HEADING = "## Section-by-Section Feedback"


def _build_feedback_note(ac_citations_result: dict, ac_coverage_result: dict | None) -> str:
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
    missing = (ac_coverage_result or {}).get("missing") or []
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


def enforce_citation_gate(
    feature_dir: str, ac_citations_result: dict, ac_coverage_result: dict | None = None
) -> dict | None:
    """Cap Scope Fidelity to 1 if the deterministic citation checks say it should be, but the
    persisted review score says 2. Returns None if TestPlanReview.md doesn't exist.
    """
    review_path = os.path.join(feature_dir, "TestPlanReview.md")
    if not os.path.exists(review_path):
        return None

    data, _ = read_frontmatter_validated(review_path, "test-plan-review")

    citations_ok = ac_citations_result.get("valid", True) and (
        ac_coverage_result is None or ac_coverage_result.get("valid", True)
    )
    scores = dict(data.get("scores", {}))
    if citations_ok or scores.get("scope_fidelity", 0) <= 1:
        return {"overridden": False}

    old_score = data.get("score")
    scores["scope_fidelity"] = 1
    verdict, score, passed = compute_verdict_and_pass(scores)

    updates = {"scores": scores, "score": score, "pass": passed, "verdict": verdict}

    # A first-pass review sets before_score/before_scores equal to score, as a same-cycle
    # mirror (see review-agent.md), not a genuine prior-cycle baseline. Left uncorrected, the
    # lowered score would look like a regression to filter_for_revision.py and get skipped.
    if data.get("before_score") == old_score:
        updates["before_score"] = score
        before_scores = dict(data.get("before_scores") or {})
        if before_scores:
            before_scores["scope_fidelity"] = 1
            updates["before_scores"] = before_scores

    update_frontmatter(review_path, updates, "test-plan-review")
    _insert_feedback_note(review_path, _build_feedback_note(ac_citations_result, ac_coverage_result))

    return {"overridden": True, "scores": scores, "score": score, "pass": passed, "verdict": verdict}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_dir")
    parser.add_argument("--ac-citations-result", required=True, help="JSON from validate.py ac-citations")
    parser.add_argument("--ac-coverage-result", default=None, help="JSON from validate.py ac-coverage")
    args = parser.parse_args()

    # exit 0 on input errors keeps the review run alive; stderr diagnostic ensures the
    # broken input/file is visible rather than silently skipping the safety gate.
    try:
        ac_citations = json.loads(args.ac_citations_result)
    except json.JSONDecodeError as exc:
        print(f"enforce_citation_gate: malformed --ac-citations-result JSON: {exc}", file=sys.stderr)
        sys.exit(0)
    if not isinstance(ac_citations, dict):
        print("enforce_citation_gate: --ac-citations-result must be a JSON object", file=sys.stderr)
        sys.exit(0)

    try:
        ac_coverage = json.loads(args.ac_coverage_result) if args.ac_coverage_result else None
    except json.JSONDecodeError as exc:
        print(f"enforce_citation_gate: malformed --ac-coverage-result JSON: {exc}", file=sys.stderr)
        sys.exit(0)
    if ac_coverage is not None and not isinstance(ac_coverage, dict):
        print("enforce_citation_gate: --ac-coverage-result must be a JSON object", file=sys.stderr)
        sys.exit(0)

    try:
        result = enforce_citation_gate(args.feature_dir, ac_citations, ac_coverage)
    except (ValidationError, OSError, yaml.YAMLError) as exc:
        print(f"enforce_citation_gate: invalid TestPlanReview.md: {exc}", file=sys.stderr)
        sys.exit(0)

    if result is None:
        print("SKIP")
        sys.exit(0)
    print("OVERRIDDEN" if result["overridden"] else "OK")


if __name__ == "__main__":
    main()
