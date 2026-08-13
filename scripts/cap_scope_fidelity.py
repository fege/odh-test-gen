#!/usr/bin/env python3
"""Deterministically cap Scope Fidelity to 1 when the citation checks say it should be, for
callers with no TestPlanReview.md to persist to. test-plan-score presents a rubric assessment
directly without writing a review file, so unlike test-plan-review it has no deterministic
backstop against a score agent that doesn't comply with its "cap Scope Fidelity when
citations/coverage are invalid" instruction. Wraps
scripts.enforce_citation_gate.cap_scope_fidelity() — the same pure logic test-plan-review's
enforce_citation_gate.py uses (that one also persists the result to disk).

Usage:
    uv run python scripts/cap_scope_fidelity.py \
        --scores-json '{"specificity":2,"grounding":2,"scope_fidelity":2,"actionability":2,"consistency":2}' \
        --ac-citations-result '<json from validate.py ac-citations>' \
        --ac-coverage-result '<json from validate.py ac-coverage>'

Exit code 0 with a JSON object to stdout: `status` is "overridden", "ok", or "error" (with an
`error` message field). Exit code 2 from argparse on missing args.
"""

import argparse
import json
import sys

from scripts.enforce_citation_gate import cap_scope_fidelity
from scripts.utils.error_utils import exit_graceful


def _fail(message: str) -> None:
    print(json.dumps({"status": "error", "error": message}))
    exit_graceful(f"cap_scope_fidelity: {message}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores-json", required=True, help="JSON object with five rubric scores (0-2 each)")
    parser.add_argument("--ac-citations-result", required=True, help="JSON from validate.py ac-citations")
    parser.add_argument("--ac-coverage-result", required=True, help="JSON from validate.py ac-coverage")
    args = parser.parse_args()

    try:
        scores = json.loads(args.scores_json)
    except json.JSONDecodeError as exc:
        _fail(f"malformed --scores-json: {exc}")

    if not isinstance(scores, dict):
        _fail("--scores-json must be a JSON object")

    try:
        ac_citations = json.loads(args.ac_citations_result)
    except json.JSONDecodeError as exc:
        _fail(f"malformed --ac-citations-result JSON: {exc}")

    try:
        ac_coverage = json.loads(args.ac_coverage_result)
    except json.JSONDecodeError as exc:
        _fail(f"malformed --ac-coverage-result JSON: {exc}")

    try:
        result = cap_scope_fidelity(scores, ac_citations, ac_coverage)
    except ValueError as exc:
        _fail(str(exc))

    if result["overridden"]:
        payload = {"status": "overridden"}
        payload.update({k: v for k, v in result.items() if k != "overridden"})
    else:
        payload = {"status": "ok", "scores": result["scores"]}
    print(json.dumps(payload))
    sys.exit(0)


if __name__ == "__main__":
    main()
