#!/usr/bin/env python3
"""Determine whether a test plan review warrants revision.

Reads TestPlanReview.md frontmatter and decides if the revise agent should run.
Rejects score regressions by recording regression metadata in `error`.

Usage:
    python3 scripts/filter_for_revision.py <feature_dir>

Output (stdout):
    REVISE   — revision agent should run
    SKIP     — no revision needed (all criteria are 2, or score regression)

Exit code 0 in all cases; check stdout for the decision.
"""

import os
import sys

from scripts.utils.frontmatter_utils import read_frontmatter_validated, update_frontmatter


def main():
    if len(sys.argv) != 2:
        print("Usage: filter_for_revision.py <feature_dir>", file=sys.stderr)
        sys.exit(1)

    feature_dir = sys.argv[1]
    review_path = os.path.join(feature_dir, "TestPlanReview.md")

    if not os.path.exists(review_path):
        print(f"No review file at {review_path}", file=sys.stderr)
        print("SKIP")
        return

    try:
        data, _ = read_frontmatter_validated(review_path, "test-plan-review")
    except Exception as e:
        print(f"Cannot read review: {e}", file=sys.stderr)
        print("SKIP")
        return

    score = data.get("score", 0)
    before_score = data.get("before_score")
    scores = data.get("scores", {})

    if before_score is not None and score < before_score:
        update_frontmatter(review_path,
                           {"error": f"score_regression:{before_score}->{score}"},
                           "test-plan-review")
        print(f"Score regressed ({before_score} -> {score}), "
              f"recording score_regression in error", file=sys.stderr)
        print("SKIP")
        return

    criteria = ("specificity", "grounding", "scope_fidelity",
                "actionability", "consistency")
    if not isinstance(scores, dict):
        print("SKIP")
        return
    if not any(isinstance(scores.get(k), int) and scores.get(k) < 2
               for k in criteria):
        print("SKIP")
        return

    print("REVISE")


if __name__ == "__main__":
    main()
