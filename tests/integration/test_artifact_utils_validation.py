import unittest

from scripts.artifact_utils import validate


def _valid_review_data():
    return {
        "feature": "kagenti_agent_templates",
        "strat_key": "RHAISTRAT-1290",
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
    }


class TestReviewSchemaValidation(unittest.TestCase):
    def test_valid_review_data_passes_validation(self):
        data = _valid_review_data()
        errors = validate(data, "test-plan-review")
        self.assertEqual(errors, [])

    def test_criterion_score_must_be_in_range(self):
        data = _valid_review_data()
        data["scores"]["specificity"] = 3
        errors = validate(data, "test-plan-review")
        self.assertTrue(
            any("scores.specificity" in err and "maximum 2" in err
                for err in errors),
            errors,
        )

    def test_total_score_must_match_scores_sum(self):
        data = _valid_review_data()
        data["score"] = 9
        errors = validate(data, "test-plan-review")
        self.assertTrue(
            any("score: expected 10 from scores.*, got 9" in err
                for err in errors),
            errors,
        )

    def test_before_score_and_before_scores_must_be_paired(self):
        data = _valid_review_data()
        data["before_score"] = 7
        errors = validate(data, "test-plan-review")
        self.assertTrue(
            any("before_score and before_scores must both be set" in err
                for err in errors),
            errors,
        )

    def test_before_score_must_match_before_scores_sum(self):
        data = _valid_review_data()
        data["before_scores"] = {
            "specificity": 2,
            "grounding": 1,
            "scope_fidelity": 2,
            "actionability": 1,
            "consistency": 1,
        }
        data["before_score"] = 8
        errors = validate(data, "test-plan-review")
        self.assertTrue(
            any("before_score: expected 7 from before_scores.*, got 8" in err
                for err in errors),
            errors,
        )
