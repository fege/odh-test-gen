"""
Unit tests for scripts/parse_test_score.py

Tests parsing test score assessment files.
"""

import json

import pytest

from scripts.parse_test_score import parse_test_score
from tests.constants import SCORE_FILE_READY, SCORE_FILE_REVISE


def test_parses_ready_verdict(tmp_path):
    """Should parse Ready verdict with high score."""
    score_file = tmp_path / "score.md"
    score_file.write_text(SCORE_FILE_READY)

    result = parse_test_score(str(score_file))
    data = json.loads(result)

    assert data['verdict'] == 'Ready'
    assert data['total_score'] == 9
    assert data['needs_revision'] is False


def test_parses_revise_verdict_with_issues(tmp_path):
    """Should parse Revise verdict and extract issues."""
    score_file = tmp_path / "score.md"
    score_file.write_text(SCORE_FILE_REVISE)

    result = parse_test_score(str(score_file))
    data = json.loads(result)

    assert data['verdict'] == 'Revise'
    assert data['total_score'] == 5
    assert data['needs_revision'] is True
    assert 'Missing error handling' in data['issues']
    assert 'Add try/except blocks' in data['issues']
