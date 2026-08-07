"""Unit tests for scripts/parse_strat.py — STRAT section extraction."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.parse_strat import _load_strat_content, main
from scripts.utils.strat_utils import (
    gate_inputs,
    parse_acceptance_criteria,
    parse_nfr,
    parse_out_of_scope,
    workflow_inputs,
)
from tests.helpers import strat_with_testability_heading
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
    STRAT_TESTABILITY_DEDUPED_AGAINST_MAIN_AC,
    STRAT_TESTABILITY_FOLDED_INTO_AC,
    STRAT_TESTABILITY_WITHOUT_MAIN_AC_SECTION,
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

    def test_acceptance_criteria_have_sequential_num(self):
        result = parse_acceptance_criteria(STRAT_AC_NUMBERED_LIST)

        assert [ac["num"] for ac in result["acceptance_criteria"]] == [1, 2, 3]

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

    def test_testability_edge_cases_folded_in_with_continued_numbering(self):
        result = parse_acceptance_criteria(STRAT_TESTABILITY_FOLDED_INTO_AC)

        assert result["found"] is True
        assert result["count"] == 4
        assert [ac["num"] for ac in result["acceptance_criteria"]] == [1, 2, 3, 4]
        assert result["acceptance_criteria"][2]["text"].startswith("Unverified status: Given")
        assert result["acceptance_criteria"][3]["text"].startswith("Malformed secret: Given")

    def test_testability_duplicate_of_main_ac_is_not_double_counted(self):
        result = parse_acceptance_criteria(STRAT_TESTABILITY_DEDUPED_AGAINST_MAIN_AC)

        assert result["found"] is True
        # 1 main AC + 1 unique Testability item; the literal duplicate is dropped.
        assert result["count"] == 2
        texts = [ac["text"] for ac in result["acceptance_criteria"]]
        assert sum("dialog opens, then samples are shown" in t for t in texts) == 1
        assert any(t.startswith("Unverified status: Given") for t in texts)

    def test_testability_without_main_ac_section_is_not_found(self):
        result = parse_acceptance_criteria(STRAT_TESTABILITY_WITHOUT_MAIN_AC_SECTION)

        assert result["found"] is False
        assert result["count"] == 0
        assert result["acceptance_criteria"] == []


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
        # A stray "*" bullet that is not a "* *Cat*: text" NFR must not be merged into Security.
        assert "stray bullet" not in security["text"]


class TestGateInputs:
    """Tests for gate_inputs — the citation gate's deterministic ac_count + nfr_categories.

    The gate only runs after Step 1.5 confirms ACs exist (it STOPs otherwise), so every case here
    has acceptance criteria; only the NFR section is optional.
    """

    def test_derives_from_real_strat(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()

        result = gate_inputs(content)

        assert result["ac_count"] == 10
        cats = result["nfr_categories"]
        assert isinstance(cats, list)
        assert "Performance" in cats
        assert "Security" in cats
        assert len(cats) == len(set(cats))  # de-duplicated

    def test_duplicate_categories_deduplicated_in_order(self):
        content = (
            "h3. Acceptance Criteria\n\n"
            "# Given a user registers a store, then it persists\n"
            "# Given a duplicate name, then it is rejected\n\n"
            "h3. Non-Functional Requirements\n\n"
            "* *Upgrade*: GET endpoints keep their shape\n"
            "* *Upgrade*: also this one\n"
            "* *Security*: namespace-scoped RBAC\n"
        )

        result = gate_inputs(content)

        assert result["ac_count"] == 2
        assert result["nfr_categories"] == ["Upgrade", "Security"]

    def test_no_nfr_section_yields_empty_categories(self):
        content = (
            "h3. Acceptance Criteria\n\n"
            "# Given a user registers a store, then it persists\n\n"
            "h3. Risks\n\nSome risks.\n"
        )

        result = gate_inputs(content)

        assert result["ac_count"] == 1
        assert result["nfr_categories"] == []

    def test_category_containing_comma_is_one_element_not_split(self):
        content = (
            "h3. Acceptance Criteria\n\n"
            "# Given a user opens the form, then it is shown\n\n"
            "h3. Non-Functional Requirements\n\n"
            "* *Security, Privacy*: data must not leave the namespace\n"
        )

        result = gate_inputs(content)

        assert result["nfr_categories"] == ["Security, Privacy"]


class TestWorkflowInputs:
    """Tests for workflow_inputs — test-plan-create's combined pre-generation gate, replacing
    four separate parse_strat.py subcommand calls plus inline jq/bash validation in SKILL.md.
    """

    def test_ok_status_combines_all_sections_from_real_strat(self):
        content = (FIXTURES_DIR / "strat-1737.md").read_text()

        result = workflow_inputs(content)

        assert result["status"] == "ok"
        assert result["ac_json"]["count"] == 10
        assert result["nfr_json"]["found"] is True
        assert result["oos_json"]["found"] is True
        assert result["ac_count"] == 10
        assert "Performance" in result["nfr_categories"]

    def test_no_acceptance_criteria_status_when_section_absent(self):
        content = "h3. Requirements\n\nSome text.\n\nh3. Risks\n\nSome risks.\n"

        result = workflow_inputs(content)

        assert result == {
            "status": "no_acceptance_criteria",
            "ac_json": {"found": False, "count": 0, "acceptance_criteria": []},
        }

    def test_no_acceptance_criteria_status_when_section_present_but_empty(self):
        content = "h3. Acceptance Criteria (Proposed -- requires PM/Engineering validation)\n\nh3. Effort Estimate\n"

        result = workflow_inputs(content)

        assert result["status"] == "no_acceptance_criteria"
        assert result["ac_json"]["found"] is True
        assert result["ac_json"]["count"] == 0

    def test_missing_nfr_and_oos_sections_preserve_found_false_not_squashed(self):
        content = (
            "h3. Acceptance Criteria\n\n"
            "# Given a user registers a store, then it persists\n\n"
            "h3. Risks\n\nSome risks.\n"
        )

        result = workflow_inputs(content)

        assert result["status"] == "ok"
        assert result["nfr_json"] == {"found": False, "requirements": []}
        assert result["oos_json"] == {"found": False, "count": 0, "items": []}
        assert result["ac_count"] == 1
        assert result["nfr_categories"] == []


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


class TestTestabilityHeadingMatch:
    """Tests that only exact or colon-qualified Testability headings fold into ACs."""

    @pytest.mark.parametrize(
        "heading",
        [
            "h3. Testability Concerns",
            "h3. Testability Notes",
        ],
    )
    def test_non_testability_heading_not_folded(self, heading):
        result = parse_acceptance_criteria(strat_with_testability_heading(heading))

        assert result["found"] is True
        assert result["count"] == 2
        ac_texts = [ac["text"] for ac in result["acceptance_criteria"]]
        assert not any("throttled" in t for t in ac_texts)

    @pytest.mark.parametrize(
        "heading",
        [
            "h3. Testability",
            "h3. Testability: Additional Acceptance Criteria",
        ],
    )
    def test_testability_heading_folds(self, heading):
        result = parse_acceptance_criteria(strat_with_testability_heading(heading))

        assert result["found"] is True
        assert result["count"] == 3
        ac_texts = [ac["text"] for ac in result["acceptance_criteria"]]
        assert any("throttled" in t for t in ac_texts)


class TestWorkflowInputsCLI:
    """CLI-level tests for parse_strat.py's workflow-inputs — exercises the strategy-file read
    failure path, which the underlying workflow_inputs() function never sees (it takes content,
    not a path).
    """

    def test_unreadable_strategy_file_exits_one_with_structured_error(self, tmp_path, capsys):
        # A directory can't be read as text — stands in for a bad/missing --strategy-file path.
        old_argv = sys.argv
        try:
            sys.argv = ["parse_strat.py", "workflow-inputs", str(tmp_path)]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("main() must exit with code 1")
        finally:
            sys.argv = old_argv

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "error"
        assert isinstance(output["error"], str) and output["error"]

    def test_strat_file_outside_permitted_roots_is_rejected(self, capsys):
        # A real, readable file — just not under the mktemp temp dir or artifacts/strat-tasks/.
        # Proves containment is enforced by location, not by whether the file happens to exist.
        outside_file = FIXTURES_DIR / "strat-1737.md"
        old_argv = sys.argv
        try:
            sys.argv = ["parse_strat.py", "workflow-inputs", str(outside_file)]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("main() must exit with code 1")
        finally:
            sys.argv = old_argv

        output = json.loads(capsys.readouterr().out)
        assert output == {"status": "error", "error": "strategy_file_unreadable"}


class TestLoadStratContentContainment:
    """Unit tests for _load_strat_content's path-containment guard, shared by all four
    subcommands. Every documented caller passes either a mktemp file or a path under
    artifacts/strat-tasks/ — anything else must be rejected before the file is read.
    """

    def test_mktemp_file_is_permitted(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=True) as f:
            f.write("h3. Acceptance Criteria\n\n# Given X, then Y\n")
            f.flush()

            assert "Given X" in _load_strat_content(f.name)

    def _isolate_temp_root(self, tmp_path, monkeypatch):
        # tmp_path itself lives under the real tempfile.gettempdir() tree, which would make the
        # temp-dir allow-rule silently cover it too. Point it somewhere structurally disjoint so
        # these tests actually exercise the artifacts/strat-tasks allow-rule in isolation.
        fake_system_tmp = tmp_path.parent / "unrelated-system-tmp"
        monkeypatch.setattr("scripts.parse_strat.tempfile.gettempdir", lambda: str(fake_system_tmp))

    def test_artifacts_strat_tasks_file_is_permitted(self, tmp_path, monkeypatch):
        self._isolate_temp_root(tmp_path, monkeypatch)
        strat_dir = tmp_path / "artifacts" / "strat-tasks"
        strat_dir.mkdir(parents=True)
        strat_file = strat_dir / "RHAISTRAT-1746.md"
        strat_file.write_text("h3. Acceptance Criteria\n\n# Given X, then Y\n")
        monkeypatch.setattr("scripts.parse_strat.get_git_root", lambda _: str(tmp_path))

        assert "Given X" in _load_strat_content(str(strat_file))

    def test_file_outside_both_permitted_roots_is_rejected(self):
        outside_file = FIXTURES_DIR / "strat-1737.md"

        with pytest.raises(ValueError, match="strategy_file_not_permitted"):
            _load_strat_content(str(outside_file))

    def test_traversal_out_of_artifacts_strat_tasks_is_rejected(self, tmp_path, monkeypatch):
        self._isolate_temp_root(tmp_path, monkeypatch)
        strat_dir = tmp_path / "artifacts" / "strat-tasks"
        strat_dir.mkdir(parents=True)
        secret_file = tmp_path / "artifacts" / "secret.md"
        secret_file.write_text("top secret")
        monkeypatch.setattr("scripts.parse_strat.get_git_root", lambda _: str(tmp_path))

        with pytest.raises(ValueError, match="strategy_file_not_permitted"):
            _load_strat_content(str(strat_dir / ".." / "secret.md"))


class TestCmdResolveLocal:
    """CLI-level tests for parse_strat.py's resolve-local — validates a Jira key before
    turning it into a filesystem path, closing the gap where test-plan-create/SKILL.md
    used to splice an unvalidated <JIRA_KEY> directly into artifacts/strat-tasks/<KEY>.md.
    """

    def _run(self, jira_key, tmp_path, monkeypatch, capsys, create_file=True):
        monkeypatch.setattr("scripts.parse_strat.get_git_root", lambda _: str(tmp_path))
        if create_file:
            strat_dir = tmp_path / "artifacts" / "strat-tasks"
            strat_dir.mkdir(parents=True)
            (strat_dir / f"{jira_key}.md").write_text("content")

        old_argv = sys.argv
        try:
            sys.argv = ["parse_strat.py", "resolve-local", jira_key]
            try:
                main()
                exit_code = 0
            except SystemExit as exc:
                exit_code = exc.code
        finally:
            sys.argv = old_argv

        return exit_code, json.loads(capsys.readouterr().out)

    def test_valid_key_with_cached_file_resolves(self, tmp_path, monkeypatch, capsys):
        exit_code, output = self._run("RHAISTRAT-1746", tmp_path, monkeypatch, capsys)

        assert exit_code == 0
        assert output["found"] is True
        assert output["strategy_file"] == str(tmp_path / "artifacts" / "strat-tasks" / "RHAISTRAT-1746.md")

    def test_valid_key_without_cached_file_fails(self, tmp_path, monkeypatch, capsys):
        exit_code, output = self._run("RHAISTRAT-9999999", tmp_path, monkeypatch, capsys, create_file=False)

        assert exit_code == 1
        assert output == {"found": False, "error": "strategy_file_not_found"}

    @pytest.mark.parametrize(
        "jira_key",
        [
            "../../etc/passwd",
            "EVILPROJ-1",  # well-shaped but not one of the three real prefixes
            "rhaistrat-1746",  # lowercase
            "RHAISTRAT-",  # missing number
            "RHAISTRAT-1746; rm -rf /",
        ],
    )
    def test_malformed_or_disallowed_key_is_rejected_before_touching_disk(
        self, jira_key, tmp_path, monkeypatch, capsys
    ):
        exit_code, output = self._run(jira_key, tmp_path, monkeypatch, capsys, create_file=False)

        assert exit_code == 1
        assert output == {"found": False, "error": "malformed_jira_key"}
