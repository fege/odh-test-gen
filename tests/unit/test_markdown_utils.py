"""Unit tests for scripts/utils/markdown_utils.py."""

import time

import pytest

from scripts.utils.markdown_utils import extract_section, has_citation, parse_citations
from tests.consts.markdown_constants import (
    EXTRACT_GAPS_DUPLICATE_HEADING,
    EXTRACT_GAPS_EMPTY_THEN_OTHER,
    EXTRACT_GAPS_LEVEL_ONE_BETWEEN,
    EXTRACT_GAPS_MISSING,
    EXTRACT_GAPS_TRAILING_WS_HEADING,
    EXTRACT_GAPS_WITH_PREFIX_SIBLING,
    EXTRACT_HEADING_HASH_IN_TITLE,
)


class TestExtractSectionHeadingMatch:
    @pytest.mark.parametrize(
        "content,heading,expected_lines,expected_start",
        [
            pytest.param(
                EXTRACT_GAPS_WITH_PREFIX_SIBLING,
                "## Gaps",
                ["- gap 1", "### Details", "- gap 2"],
                3,
                id="prefix-sibling",
            ),
            pytest.param(EXTRACT_GAPS_DUPLICATE_HEADING, "## Gaps", ["- first"], 2, id="duplicate-heading"),
            pytest.param(EXTRACT_GAPS_TRAILING_WS_HEADING, "## Gaps", ["- gap"], 2, id="trailing-whitespace"),
            pytest.param(EXTRACT_GAPS_EMPTY_THEN_OTHER, "## Gaps", [], 2, id="empty-section"),
            pytest.param(EXTRACT_GAPS_LEVEL_ONE_BETWEEN, "## Gaps", ["- gap"], 2, id="level-one-terminates"),
            pytest.param(EXTRACT_GAPS_MISSING, "## Gaps", [], 0, id="missing-heading"),
            pytest.param(
                EXTRACT_HEADING_HASH_IN_TITLE,
                "## C#",
                ["- gap", "### Details", "- child"],
                2,
                id="hash-in-title",
            ),
        ],
    )
    def test_complete_heading_first_match_only(self, content, heading, expected_lines, expected_start):
        lines, start = extract_section(content, heading)

        assert lines == expected_lines
        assert start == expected_start


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

    def test_hyphenated_nfr_category_is_not_truncated_at_the_intra_word_hyphen(self):
        # "Multi-tenancy" has no whitespace around its internal hyphen, unlike the em-dash
        # separator before the rationale — the hyphen must not be mistaken for the separator.
        text = "Verify isolation (NFR: Multi-tenancy — data is isolated)"
        assert has_citation(text) is True
        assert parse_citations(text)[0] == {"kind": "NFR", "number": None, "category": "Multi-tenancy"}

    def test_nfr_category_with_parenthetical_qualifier_is_not_truncated(self):
        # Real STRAT documents define sibling categories that differ only by a parenthetical
        # qualifier, e.g. "Security" vs "Security (workspace isolation)" vs "Security (transport)" —
        # the inner ")" must not be mistaken for the citation's own closing paren.
        text = "Verify namespace scoping (NFR: Security (workspace isolation) — tenant isolation required)"
        assert has_citation(text) is True
        assert parse_citations(text)[0] == {
            "kind": "NFR",
            "number": None,
            "category": "Security (workspace isolation)",
        }

    def test_bare_nfr_category_still_distinct_from_parenthetical_sibling(self):
        text = "Verify auth (NFR: Security — SA-token auth required)"
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


# ---------------------------------------------------------------------------
# ReDoS regression guard — quadratic backtracking in CITATION_RE / _NFR_CITATION_RE
# ---------------------------------------------------------------------------
# The unbounded `[^\-\u2013\u2014)]*` and `[^)]*` quantifiers in the NFR branch
# of CITATION_RE cause O(n^2) backtracking on inputs that open `(NFR:` but never
# supply the required dash separator or closing paren.
#
# The fix is to bound those quantifiers to a finite width (≤ 1024 chars each).
# After the fix all five tests below must be GREEN.  Before the fix the two
# time-budget tests are RED — but note that they are *slow* failures: the
# pathological input causes ~85 s of regex scanning before the assertion fires.
# Run this class in isolation if you only want the ReDoS signal:
#
#   uv run pytest tests/unit/test_markdown_utils.py::TestCitationRegexRedosBounds -v
#
# WARNING: running the two `_parse_citations` / `_has_citation` time-budget
# tests against the *unfixed* code will block for approximately 1–2 minutes
# before they fail the time assertion.  That is expected behaviour for a ReDoS
# guard — the slow hang is precisely the vulnerability being measured.
@pytest.mark.slow
class TestCitationRegexRedosBounds:
    """Regression guard: citation regex must not exhibit quadratic backtracking."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pathological_input(repeats: int = 20_000) -> str:
        """Return a string of repeated unterminated NFR prefixes.

        Each unit ``"(NFR: incomplete "`` opens the NFR citation branch but
        never delivers the required dash separator or closing paren.  With
        unbounded quantifiers the engine rescans the growing tail on every
        attempt, producing O(n²) behaviour.  The total size is ~340 KB at
        20 000 repeats.
        """
        return "(NFR: incomplete " * repeats

    # ------------------------------------------------------------------
    # Time-budget regression tests (RED against unfixed code, GREEN after fix)
    # ------------------------------------------------------------------

    def test_parse_citations_pathological_input_completes_within_budget(self):
        """parse_citations must finish in under 2 s on a 20 000-repeat pathological input.

        RED now (unfixed CITATION_RE takes ~85 s → assertion fires after ~85 s).
        GREEN after bounding the unbounded quantifiers to ≤ 512 chars.

        WARNING: against the *unfixed* code this test will hang for ~1–2 minutes
        before the time assertion fails.  That long wait is the vulnerability.
        """
        text = self._pathological_input(repeats=20_000)
        _BUDGET_SECONDS = 2.0

        start = time.perf_counter()
        result = parse_citations(text)
        elapsed = time.perf_counter() - start

        assert elapsed < _BUDGET_SECONDS, (
            f"citation scan took {elapsed:.2f}s — possible ReDoS regression "
            f"(budget {_BUDGET_SECONDS}s).  The unbounded quantifiers in CITATION_RE "
            "are likely still present."
        )
        # Unterminated prefixes must never produce a citation — no false positives.
        assert result == [], "unterminated NFR prefixes must not be parsed as citations"

    def test_has_citation_pathological_input_completes_within_budget(self):
        """has_citation must finish in under 2 s on a 20 000-repeat pathological input.

        This exercises CITATION_RE.search (the early-exit path) under the same
        adversarial input.  Same RED/GREEN status and same ~1–2 min hang warning
        as the parse_citations variant above.
        """
        text = self._pathological_input(repeats=20_000)
        _BUDGET_SECONDS = 2.0

        start = time.perf_counter()
        found = has_citation(text)
        elapsed = time.perf_counter() - start

        assert elapsed < _BUDGET_SECONDS, (
            f"has_citation took {elapsed:.2f}s — possible ReDoS regression (budget {_BUDGET_SECONDS}s)."
        )
        assert found is False, "unterminated NFR prefixes must not be recognised as citations"

    # ------------------------------------------------------------------
    # Behaviour-preservation tests (GREEN now, must stay GREEN after fix)
    # ------------------------------------------------------------------

    def test_nfr_citation_at_bound_boundary_is_recognised(self):
        """An NFR citation whose category and rationale each approach the future 1024-char
        bound must still parse correctly.

        This test is GREEN now and must stay GREEN after the quantifier is bounded,
        proving the fix does not truncate legitimate citations that are long but finite.
        """
        category = "A" * 1000
        rationale = "B" * 1000
        text = f"(NFR: {category} \u2014 {rationale})"

        assert has_citation(text) is True, (
            "a well-formed NFR citation with category/rationale of ~1000 chars must be recognised"
        )
        citations = parse_citations(text)
        assert citations, "parse_citations must return at least one citation for a valid NFR"
        assert citations[0]["kind"] == "NFR"
        assert citations[0]["category"] == category

    def test_short_ac_citation_still_recognised_after_bound(self):
        """A normal short AC citation must remain parseable — sanity check that the fix
        does not regress the common case.

        GREEN now, must stay GREEN after the fix.
        """
        text = "(AC: #1 \u2014 ok)"

        assert has_citation(text) is True
        citations = parse_citations(text)
        assert citations == [{"kind": "AC", "number": 1, "category": None}]

    def test_short_nfr_citation_still_recognised_after_bound(self):
        """A normal short NFR citation must remain parseable — sanity check that the fix
        does not regress the common case.

        GREEN now, must stay GREEN after the fix.
        """
        text = "(NFR: Security \u2014 ok)"

        assert has_citation(text) is True
        citations = parse_citations(text)
        assert citations == [{"kind": "NFR", "number": None, "category": "Security"}]
