"""Unit tests for scripts/parse_strat.py — STRAT section extraction."""

from pathlib import Path


from scripts.utils.strat_utils import (
    parse_acceptance_criteria,
    parse_nfr,
    parse_out_of_scope,
)
from tests.constants import (
    STRAT_AC_NUMBERED_LIST,
    STRAT_AC_NUMBERED_MULTI_PARAGRAPH,
    STRAT_AC_NUMBERED_NO_BLANK_LINES,
    STRAT_AC_NUMBERED_SINGLE_LINE,
    STRAT_AC_STAR_BULLETS_NO_BLANK_LINES,
    STRAT_NFR_WRAPPED_BULLET,
    STRAT_OOS_EM_DASH,
    STRAT_OOS_MIXED,
    STRAT_OOS_PLAIN_TEXT,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestParseAcceptanceCriteria:
    """Tests for acceptance criteria extraction from fetched STRAT content."""

    def test_extracts_acs_from_real_strat(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()

        result = parse_acceptance_criteria(content)

        assert result["found"] is True
        assert result["count"] == 10
        assert all("Given" in ac["text"] or "given" in ac["text"] for ac in result["acceptance_criteria"])

    def test_no_ac_section(self):
        content = "h2. Strategy\n\nh3. Requirements\n\nSome text.\n\nh3. Risks\n\nSome risks.\n"

        result = parse_acceptance_criteria(content)

        assert result["found"] is False
        assert result["count"] == 0
        assert result["acceptance_criteria"] == []

    def test_empty_ac_section(self):
        content = "h3. Acceptance Criteria (Proposed -- requires PM/Engineering validation)\n\nh3. Effort Estimate\n"

        result = parse_acceptance_criteria(content)

        assert result["found"] is True
        assert result["count"] == 0

    def test_multiline_ac_parsed_as_single_item(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()

        result = parse_acceptance_criteria(content)

        first_ac = result["acceptance_criteria"][0]["text"]
        assert "Given" in first_ac
        assert "measured by" in first_ac

    def test_numbered_list_acs_joined(self):
        result = parse_acceptance_criteria(STRAT_AC_NUMBERED_LIST)

        assert result["found"] is True
        assert result["count"] == 3
        assert "Given a user opens" in result["acceptance_criteria"][0]["text"]
        assert "measured by rendering" in result["acceptance_criteria"][0]["text"]
        assert "Given a user clicks" in result["acceptance_criteria"][1]["text"]
        assert "measured by card count" in result["acceptance_criteria"][1]["text"]

    def test_numbered_list_acs_single_line(self):
        result = parse_acceptance_criteria(STRAT_AC_NUMBERED_SINGLE_LINE)

        assert result["found"] is True
        assert result["count"] == 2

    def test_numbered_list_acs_three_paragraphs_merged(self):
        result = parse_acceptance_criteria(STRAT_AC_NUMBERED_MULTI_PARAGRAPH)

        assert result["found"] is True
        assert result["count"] == 2
        first = result["acceptance_criteria"][0]["text"]
        assert "registers a vector store" in first
        assert "measured by API response" in first

    def test_numbered_list_acs_no_blank_lines_between_entries(self):
        result = parse_acceptance_criteria(STRAT_AC_NUMBERED_NO_BLANK_LINES)

        assert result["found"] is True
        assert result["count"] == 3
        assert "Given a user opens" in result["acceptance_criteria"][0]["text"]
        assert "Given a user clicks" in result["acceptance_criteria"][1]["text"]
        assert "Given the dialog is open" in result["acceptance_criteria"][2]["text"]

    def test_star_bulleted_acs_no_blank_lines_between_entries(self):
        result = parse_acceptance_criteria(STRAT_AC_STAR_BULLETS_NO_BLANK_LINES)

        assert result["found"] is True
        assert result["count"] == 3
        assert "Given a user opens the form" in result["acceptance_criteria"][0]["text"]
        assert "Given a user submits invalid input" in result["acceptance_criteria"][1]["text"]
        assert "Given a duplicate name is submitted" in result["acceptance_criteria"][2]["text"]


class TestParseNfr:
    """Tests for non-functional requirements extraction from fetched STRAT content."""

    def test_extracts_nfrs_from_real_strat(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()

        result = parse_nfr(content)

        assert result["found"] is True
        categories = [nfr["category"] for nfr in result["requirements"]]
        assert "Performance" in categories
        assert "Security" in categories
        assert "Backwards Compatibility" in categories
        assert "Scalability" in categories

    def test_no_nfr_section(self):
        content = "h3. Requirements\n\nSome text.\n\nh3. Risks\n\nSome risks.\n"

        result = parse_nfr(content)

        assert result["found"] is False
        assert result["requirements"] == []

    def test_wrapped_bullet_not_truncated(self):
        result = parse_nfr(STRAT_NFR_WRAPPED_BULLET)

        assert result["found"] is True
        security = next(nfr for nfr in result["requirements"] if nfr["category"] == "Security")
        assert "namespace isolation" in security["text"]
        assert "with all other BFF endpoints" in security["text"]


class TestParseOutOfScope:
    """Tests for out-of-scope extraction from fetched STRAT content."""

    def test_extracts_out_of_scope_from_real_strat(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()

        result = parse_out_of_scope(content)

        assert result["found"] is True
        assert result["count"] >= 5
        assert all(item["title"] for item in result["items"])

    def test_plain_text_bullets(self):
        result = parse_out_of_scope(STRAT_OOS_PLAIN_TEXT)

        assert result["found"] is True
        assert result["count"] == 5
        assert "Custom management UI" in result["items"][0]["text"]

    def test_em_dash_separator(self):
        result = parse_out_of_scope(STRAT_OOS_EM_DASH)

        assert result["found"] is True
        assert result["count"] == 1
        assert result["items"][0]["title"] == "Backend API"

    def test_mixed_bold_and_plain_bullets(self):
        result = parse_out_of_scope(STRAT_OOS_MIXED)

        assert result["found"] is True
        assert result["count"] == 3

    def test_no_out_of_scope_section(self):
        content = "h3. Requirements\n\nSome text.\n\nh3. Risks\n\nSome risks.\n"

        result = parse_out_of_scope(content)

        assert result["found"] is False
        assert result["items"] == []
