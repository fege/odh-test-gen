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

    def test_bare_ac_marker_before_complete_nfr_citation_parses_the_nfr(self):
        # A bare, incomplete (AC: #N) sitting earlier in the text must not hijack parsing away
        # from the actual complete citation that follows it.
        text = "Verify something (AC: #1) additionally (NFR: Upgrade — shape kept)"

        assert has_citation(text) is True
        assert parse_citation(text) == {"kind": "NFR", "number": None, "category": "Upgrade"}

    def test_bare_nfr_marker_before_complete_ac_citation_parses_the_ac(self):
        text = "Verify something (NFR: Upgrade) additionally (AC: #2 — deploy succeeds)"

        assert has_citation(text) is True
        assert parse_citation(text) == {"kind": "AC", "number": 2, "category": None}


class TestCitationRejectsIncompleteFields:
    """
    The documented format requires:
      - AC: a non-empty #N reference, the em-dash U+2014, non-whitespace explanatory text, and ')'
      - NFR: a non-empty category name (not just whitespace), the em-dash, non-whitespace text, ')'
    A rationale composed only of whitespace, or an NFR with no category at all, is NOT a valid
    citation even though the em-dash and closing paren are structurally present.
    """

    def test_ac_whitespace_only_rationale_has_citation_is_false(self):
        # The rationale after the em-dash is three spaces — structurally complete but semantically
        # empty.  has_citation must return False.
        text = "Verify something (AC: #1 —   )"
        assert has_citation(text) is False

    def test_ac_whitespace_only_rationale_parse_citation_is_none(self):
        text = "Verify something (AC: #1 —   )"
        assert parse_citation(text) is None

    def test_nfr_empty_category_has_citation_is_false(self):
        # Category field is absent between "NFR:" and the em-dash.
        # has_citation must return False — an NFR with no category is not a valid citation.
        text = "Verify something (NFR: — some rationale)"
        assert has_citation(text) is False

    def test_nfr_empty_category_parse_citation_is_none(self):
        text = "Verify something (NFR: — some rationale)"
        assert parse_citation(text) is None

    # ---- Positive controls: valid citations still parse correctly after the regex tightening ----

    def test_complete_ac_citation_still_recognized(self):
        text = "Verify deployment (AC: #3 — users can deploy the model)"
        assert has_citation(text) is True
        assert parse_citation(text) == {"kind": "AC", "number": 3, "category": None}

    def test_complete_nfr_citation_still_recognized(self):
        text = "Verify upgrade path (NFR: Security — namespace isolation enforced)"
        assert has_citation(text) is True
        assert parse_citation(text) == {"kind": "NFR", "number": None, "category": "Security"}
