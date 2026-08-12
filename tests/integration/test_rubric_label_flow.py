"""Integration tests: real TestPlanReview.md rubric state -> correct Jira label.

No Jira/network involvement -- verifies the full local chain from a real,
schema-validated review file's stored verdict to the label that
skills/test-plan-create/SKILL.md Step 4.5 would stamp, via
rubric_label_for_verdict().
"""

import os

import pytest

from scripts.add_jira_labels import rubric_label_for_verdict
from scripts.utils.frontmatter_utils import read_frontmatter_validated, write_frontmatter_with_body
from tests.helpers import build_review_payload


def _write_review(feature_dir, scores, score, verdict, passed):
    review_path = os.path.join(feature_dir, "TestPlanReview.md")
    data = build_review_payload(scores, score=score, verdict=verdict, passed=passed)
    return write_frontmatter_with_body(review_path, "## Test Plan Review\n", data, "test-plan-review")


@pytest.mark.parametrize(
    "scores,score,verdict,passed,expected_label",
    [
        (
            {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 2, "consistency": 2},
            10,
            "Ready",
            True,
            "test-plan-rubric-pass",
        ),
        (
            {"specificity": 2, "grounding": 2, "scope_fidelity": 2, "actionability": 1, "consistency": 2},
            9,
            "Revise",
            True,
            "test-plan-rubric-revise",
        ),
        (
            {"specificity": 1, "grounding": 1, "scope_fidelity": 1, "actionability": 1, "consistency": 1},
            5,
            "Rework",
            False,
            "test-plan-rubric-fail",
        ),
    ],
)
def test_rubric_state_maps_to_correct_label(tmp_path, scores, score, verdict, passed, expected_label):
    review_path = _write_review(tmp_path, scores, score, verdict, passed)

    data, _ = read_frontmatter_validated(review_path, "test-plan-review")

    assert rubric_label_for_verdict(data["verdict"]) == expected_label
