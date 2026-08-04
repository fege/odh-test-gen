"""Unit tests for scripts/utils/markdown_utils.py — citation parsing."""

import pytest

from scripts.utils.markdown_utils import has_citation, parse_citation


class TestCitationParsing:
    """Tests for has_citation/parse_citation — (AC: #N — text) / (NFR: category — text)."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("(AC: #1 — first)", {"kind": "AC", "number": 1, "category": None}),
            ("(NFR: Upgrade — shape kept)", {"kind": "NFR", "number": None, "category": "Upgrade"}),
        ],
        ids=["complete-ac", "complete-nfr"],
    )
    def test_complete_citation_parses(self, text, expected):
        assert has_citation(text) is True
        assert parse_citation(text) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "(AC: #1)",
            "(NFR: Upgrade)",
            "(AC: #1 — unterminated, no closing paren",
            "(NFR: Upgrade — unterminated, no closing paren",
        ],
        ids=["bare-ac", "bare-nfr", "unterminated-ac", "unterminated-nfr"],
    )
    def test_incomplete_citation_is_not_recognized(self, text):
        # A bare (AC: #N)/(NFR: category) with no " — text)", or a citation with no closing
        # paren at all, must not be recognized as a citation just because the identifier looks
        # valid — the documented format requires the em-dash, explanatory text, and closing paren.
        assert has_citation(text) is False
        assert parse_citation(text) is None
