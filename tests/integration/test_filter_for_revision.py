import os
import shutil
import tempfile
import unittest

from scripts.filter_for_revision import filter_for_revision
from scripts.utils.frontmatter_utils import read_frontmatter_validated, write_frontmatter


def _write_review(feature_dir, payload):
    review_path = os.path.join(feature_dir, "TestPlanReview.md")
    with open(review_path, "w", encoding="utf-8") as f:
        f.write("## Test Plan Review\n")
    write_frontmatter(review_path, payload, "test-plan-review")
    return review_path


class TestFilterForRevision(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="test-plan-filter-")

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_revise_when_any_criterion_below_two_even_if_rework(self):
        _write_review(
            self.tempdir,
            {
                "feature": "feature_a",
                "source_key": "RHAISTRAT-1000",
                "score": 5,
                "pass": False,
                "verdict": "Rework",
                "scores": {
                    "specificity": 1,
                    "grounding": 1,
                    "scope_fidelity": 1,
                    "actionability": 1,
                    "consistency": 1,
                },
                "auto_revised": False,
                "before_score": None,
                "before_scores": None,
                "error": None,
                "last_updated": "2026-04-10",
            },
        )
        result = filter_for_revision(self.tempdir)
        self.assertEqual(result, "REVISE")

    def test_skip_when_all_criteria_are_two(self):
        _write_review(
            self.tempdir,
            {
                "feature": "feature_b",
                "source_key": "RHAISTRAT-1001",
                "score": 10,
                "pass": True,
                "verdict": "Ready",
                "scores": {
                    "specificity": 2,
                    "grounding": 2,
                    "scope_fidelity": 2,
                    "actionability": 2,
                    "consistency": 2,
                },
                "auto_revised": False,
                "before_score": None,
                "before_scores": None,
                "error": None,
                "last_updated": "2026-04-10",
            },
        )
        result = filter_for_revision(self.tempdir)
        self.assertEqual(result, "SKIP")

    def test_score_regression_records_error_and_skips(self):
        _write_review(
            self.tempdir,
            {
                "feature": "feature_c",
                "source_key": "RHAISTRAT-1002",
                "score": 7,
                "pass": True,
                "verdict": "Revise",
                "scores": {
                    "specificity": 2,
                    "grounding": 1,
                    "scope_fidelity": 2,
                    "actionability": 1,
                    "consistency": 1,
                },
                "auto_revised": False,
                "before_score": 8,
                "before_scores": {
                    "specificity": 2,
                    "grounding": 2,
                    "scope_fidelity": 2,
                    "actionability": 1,
                    "consistency": 1,
                },
                "error": None,
                "last_updated": "2026-04-10",
            },
        )
        result = filter_for_revision(self.tempdir)
        self.assertEqual(result, "SKIP")

        review_path = os.path.join(self.tempdir, "TestPlanReview.md")
        data, _ = read_frontmatter_validated(review_path, "test-plan-review")
        self.assertEqual(data["verdict"], "Revise")
        self.assertEqual(data["error"], "score_regression:8->7")
