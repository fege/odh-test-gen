import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.artifact_utils import read_frontmatter_validated, write_frontmatter


FILTER_SCRIPT = str(Path(__file__).parent.parent.parent / "scripts" / "filter_for_revision.py")


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

    def _run_filter(self):
        return subprocess.run(
            [sys.executable, FILTER_SCRIPT, self.tempdir],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_revise_when_any_criterion_below_two_even_if_rework(self):
        _write_review(
            self.tempdir,
            {
                "feature": "feature_a",
                "strat_key": "RHAISTRAT-1000",
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
        result = self._run_filter()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "REVISE")

    def test_skip_when_all_criteria_are_two(self):
        _write_review(
            self.tempdir,
            {
                "feature": "feature_b",
                "strat_key": "RHAISTRAT-1001",
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
        result = self._run_filter()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "SKIP")

    def test_score_regression_records_error_and_skips(self):
        _write_review(
            self.tempdir,
            {
                "feature": "feature_c",
                "strat_key": "RHAISTRAT-1002",
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
        result = self._run_filter()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "SKIP")

        review_path = os.path.join(self.tempdir, "TestPlanReview.md")
        data, _ = read_frontmatter_validated(review_path, "test-plan-review")
        self.assertEqual(data["verdict"], "Revise")
        self.assertEqual(data["error"], "score_regression:8->7")
