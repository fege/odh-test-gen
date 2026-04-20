import json
import os
import shutil
import tempfile
import unittest

from scripts.utils.frontmatter_utils import read_frontmatter_validated, write_frontmatter
from scripts import preserve_review_state


def _base_review_payload():
    return {
        "feature": "kagenti_agent_templates",
        "source_key": "RHAISTRAT-1290",
        "score": 8,
        "pass": True,
        "verdict": "Revise",
        "scores": {
            "specificity": 2,
            "grounding": 2,
            "scope_fidelity": 2,
            "actionability": 1,
            "consistency": 1,
        },
        "auto_revised": False,
        "before_score": None,
        "before_scores": None,
        "error": None,
        "last_updated": "2026-04-10",
    }


def _write_review(feature_dir, revision_history):
    review_path = os.path.join(feature_dir, "TestPlanReview.md")
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(
            "## Test Plan Review\n\n"
            "## Revision History\n"
            f"{revision_history}\n\n"
            "## Notes\n"
            "- review body placeholder\n"
        )
    write_frontmatter(review_path, _base_review_payload(), "test-plan-review")
    return review_path


def _write_state(feature_dir, revision_history):
    state_path = os.path.join(feature_dir, ".review-state.json")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "before_score": 8,
                "before_scores": {
                    "specificity": 2,
                    "grounding": 2,
                    "scope_fidelity": 2,
                    "actionability": 1,
                    "consistency": 1,
                },
                "revision_history": revision_history,
            },
            f,
            indent=2,
        )


class TestPreserveReviewState(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="test-plan-preserve-state-")

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_restore_replaces_placeholder_history(self):
        saved_history = "### Cycle 1 Revision\n- tightened endpoint mapping"
        review_path = _write_review(self.tempdir, "Initial assessment")
        _write_state(self.tempdir, saved_history)

        preserve_review_state.restore(self.tempdir)

        final_history = preserve_review_state._extract_revision_history(review_path)
        self.assertEqual(final_history, saved_history)
        self.assertNotIn("Initial assessment", final_history)

        data, _ = read_frontmatter_validated(review_path, "test-plan-review")
        self.assertEqual(data["before_score"], 8)
        self.assertEqual(data["before_scores"]["specificity"], 2)

    def test_restore_merges_saved_and_new_history_when_new_is_meaningful(self):
        saved_history = "### Cycle 1 Revision\n- added endpoint/method matrix"
        current_history = "### Cycle 2 Reassessment\n- score improved to 9/10"
        review_path = _write_review(self.tempdir, current_history)
        _write_state(self.tempdir, saved_history)

        preserve_review_state.restore(self.tempdir)

        final_history = preserve_review_state._extract_revision_history(review_path)
        self.assertEqual(final_history, f"{saved_history}\n\n{current_history}")

    def test_restore_does_not_duplicate_history_when_already_prefixed(self):
        saved_history = "### Cycle 1 Revision\n- tightened scope fidelity notes"
        current_history = (
            f"{saved_history}\n\n"
            "### Cycle 2 Reassessment\n"
            "- no further changes needed"
        )
        review_path = _write_review(self.tempdir, current_history)
        _write_state(self.tempdir, saved_history)

        preserve_review_state.restore(self.tempdir)

        final_history = preserve_review_state._extract_revision_history(review_path)
        self.assertEqual(final_history, current_history)
        self.assertEqual(final_history.count("### Cycle 1 Revision"), 1)
