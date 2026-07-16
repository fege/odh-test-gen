"""Unit tests for scripts/parse_strat.py — STRAT section extraction."""

from pathlib import Path


from scripts.utils.strat_utils import (
    generate_objective_stubs,
    parse_acceptance_criteria,
    parse_nfr,
    parse_out_of_scope,
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


class TestParseOutOfScope:
    """Tests for out-of-scope extraction from fetched STRAT content."""

    def test_extracts_out_of_scope_from_real_strat(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()

        result = parse_out_of_scope(content)

        assert result["found"] is True
        assert result["count"] >= 5
        assert all(item["title"] for item in result["items"])

    def test_no_out_of_scope_section(self):
        content = "h3. Requirements\n\nSome text.\n\nh3. Risks\n\nSome risks.\n"

        result = parse_out_of_scope(content)

        assert result["found"] is False
        assert result["items"] == []


class TestGenerateObjectiveStubs:
    """Tests for deterministic AC objective stub generation."""

    def test_generates_one_stub_per_ac(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()
        ac_result = parse_acceptance_criteria(content)

        stubs = generate_objective_stubs(ac_result)

        assert len(stubs) == ac_result["count"]

    def test_stubs_have_numbered_ac_references(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()
        ac_result = parse_acceptance_criteria(content)

        stubs = generate_objective_stubs(ac_result)

        for i, stub in enumerate(stubs, 1):
            assert stub.startswith(f"{i}. Verify ")
            assert f"(AC: #{i})" in stub

    def test_stubs_contain_fill_marker(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()
        ac_result = parse_acceptance_criteria(content)

        stubs = generate_objective_stubs(ac_result)

        for stub in stubs:
            assert "[FILL]" in stub

    def test_empty_ac_returns_empty_stubs(self):
        ac_result = {"found": False, "count": 0, "acceptance_criteria": []}

        stubs = generate_objective_stubs(ac_result)

        assert stubs == []
