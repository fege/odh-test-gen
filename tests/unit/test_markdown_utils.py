"""Unit tests for scripts/utils/markdown_utils.py — citation parsing."""

import pytest

from scripts.utils.markdown_utils import has_citation, parse_citations


class TestCitationParsing:
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
        assert parse_citations(text)[0] == expected

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
        assert has_citation(text) is False
        assert parse_citations(text) == []

    def test_bare_ac_marker_before_complete_nfr_citation_parses_the_nfr(self):
        text = "Verify something (AC: #1) additionally (NFR: Upgrade — shape kept)"

        assert has_citation(text) is True
        assert parse_citations(text)[0] == {"kind": "NFR", "number": None, "category": "Upgrade"}

    def test_bare_nfr_marker_before_complete_ac_citation_parses_the_ac(self):
        text = "Verify something (NFR: Upgrade) additionally (AC: #2 — deploy succeeds)"

        assert has_citation(text) is True
        assert parse_citations(text)[0] == {"kind": "AC", "number": 2, "category": None}


class TestCitationRejectsIncompleteFields:
    """AC and NFR citations require non-whitespace rationale and a non-empty category respectively."""

    def test_ac_whitespace_only_rationale_has_citation_is_false(self):
        text = "Verify something (AC: #1 —   )"
        assert has_citation(text) is False

    def test_ac_whitespace_only_rationale_parse_citations_is_empty(self):
        text = "Verify something (AC: #1 —   )"
        assert parse_citations(text) == []

    def test_nfr_empty_category_has_citation_is_false(self):
        text = "Verify something (NFR: — some rationale)"
        assert has_citation(text) is False

    def test_nfr_empty_category_parse_citations_is_empty(self):
        text = "Verify something (NFR: — some rationale)"
        assert parse_citations(text) == []

    def test_complete_ac_citation_still_recognized(self):
        text = "Verify deployment (AC: #3 — users can deploy the model)"
        assert has_citation(text) is True
        assert parse_citations(text)[0] == {"kind": "AC", "number": 3, "category": None}

    def test_complete_nfr_citation_still_recognized(self):
        text = "Verify upgrade path (NFR: Security — namespace isolation enforced)"
        assert has_citation(text) is True
        assert parse_citations(text)[0] == {"kind": "NFR", "number": None, "category": "Security"}


class TestCitationSeparatorVariants:
    """The separator must accept ASCII hyphen, en dash, and em dash interchangeably."""

    @pytest.mark.parametrize(
        "text, expected_result",
        [
            ("1. Validate login (AC: #2 - auth works)", True),
            ("1. Validate login (AC: #2 \u2013 auth works)", True),
            ("1. Validate login (AC: #2 \u2014 auth works)", True),
            ("1. Enforce isolation (NFR: security - namespace must be isolated)", True),
            ("1. Enforce isolation (NFR: security \u2013 namespace must be isolated)", True),
            ("1. Enforce isolation (NFR: security \u2014 namespace must be isolated)", True),
            ("1. Validate login (AC: #1)", False),
        ],
        ids=[
            "ac-ascii-hyphen",
            "ac-en-dash",
            "ac-em-dash",
            "nfr-ascii-hyphen",
            "nfr-en-dash",
            "nfr-em-dash",
            "dash-none-bare-ac",
        ],
    )
    def test_has_citation_separator_variants(self, text, expected_result):
        assert has_citation(text) is expected_result

    @pytest.mark.parametrize(
        "text, expected_first",
        [
            (
                "1. Validate login (AC: #2 - auth works)",
                {"kind": "AC", "number": 2, "category": None},
            ),
            (
                "1. Validate login (AC: #2 \u2013 auth works)",
                {"kind": "AC", "number": 2, "category": None},
            ),
            (
                "1. Validate login (AC: #2 \u2014 auth works)",
                {"kind": "AC", "number": 2, "category": None},
            ),
            (
                "1. Enforce isolation (NFR: security - namespace must be isolated)",
                {"kind": "NFR", "number": None, "category": "security"},
            ),
            (
                "1. Enforce isolation (NFR: security \u2013 namespace must be isolated)",
                {"kind": "NFR", "number": None, "category": "security"},
            ),
            (
                "1. Enforce isolation (NFR: security \u2014 namespace must be isolated)",
                {"kind": "NFR", "number": None, "category": "security"},
            ),
            ("1. Validate login (AC: #1)", None),
        ],
        ids=[
            "ac-ascii-hyphen",
            "ac-en-dash",
            "ac-em-dash",
            "nfr-ascii-hyphen",
            "nfr-en-dash",
            "nfr-em-dash",
            "dash-none-bare-ac",
        ],
    )
    def test_parse_citations_separator_variants(self, text, expected_first):
        # None in the parametrize table means the original returned None → expect empty list.
        if expected_first is None:
            assert parse_citations(text) == []
        else:
            assert parse_citations(text)[0] == expected_first


class TestParseCitationsMultiple:
    """parse_citations returns ALL citations in left-to-right document order."""

    def test_two_ac_citations_returned_in_order(self):
        text = "Verify flows (AC: #1 — first check) (AC: #2 — second check)"

        result = parse_citations(text)

        assert result == [
            {"kind": "AC", "number": 1, "category": None},
            {"kind": "AC", "number": 2, "category": None},
        ]

    def test_ac_then_nfr_citation_returned_in_order(self):
        text = "Verify flows (AC: #3 — user can deploy) (NFR: security — namespace isolated)"

        result = parse_citations(text)

        assert result == [
            {"kind": "AC", "number": 3, "category": None},
            {"kind": "NFR", "number": None, "category": "security"},
        ]

    def test_nfr_then_ac_order_is_preserved(self):
        text = "Verify flows (NFR: perf — latency under 200ms) (AC: #4 — users see fast results)"

        result = parse_citations(text)

        assert result == [
            {"kind": "NFR", "number": None, "category": "perf"},
            {"kind": "AC", "number": 4, "category": None},
        ]

    def test_no_citation_returns_empty_list(self):
        text = "Verify that the system boots correctly without any citation marker"

        assert parse_citations(text) == []

    def test_single_citation_returns_single_element_list(self):
        text = "Verify something (AC: #5 — deployment succeeds)"

        result = parse_citations(text)

        assert len(result) == 1
        assert result[0] == {"kind": "AC", "number": 5, "category": None}

    def test_bare_citation_mixed_with_real_citation_only_real_returned(self):
        text = "Verify flows (AC: #1) then also (AC: #2 — passes smoke tests)"

        result = parse_citations(text)

        assert result == [{"kind": "AC", "number": 2, "category": None}]

    def test_two_nfr_citations_returned_in_order(self):
        text = (
            "Verify non-functional aspects "
            "(NFR: security — data must not escape namespace) "
            "(NFR: performance — response under 500ms)"
        )

        result = parse_citations(text)

        assert result == [
            {"kind": "NFR", "number": None, "category": "security"},
            {"kind": "NFR", "number": None, "category": "performance"},
        ]

    def test_em_and_en_dash_in_multi_citation_line(self):
        text = "Verify flows (AC: #1 \u2014 em-dash check) (AC: #2 \u2013 en-dash check)"

        result = parse_citations(text)

        assert result == [
            {"kind": "AC", "number": 1, "category": None},
            {"kind": "AC", "number": 2, "category": None},
        ]
