"""Unit tests for test-plan.ui-verify Python utilities.

Covers pure functions that require no browser, network, or Playwright:
  - helpers.is_ui_test / helpers.matches_tc_filter
  - build_element_map.classify_file
  - ui_assert.update_log  (file I/O mocked via tmp path)

All imports are done inside test classes so the sys.path insertion
runs before each module is loaded.
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add the skill's scripts/ directory to sys.path so skill modules are importable.
_SKILL_SCRIPTS = (
    Path(__file__).resolve().parent.parent.parent
    / "skills" / "test-plan-ui-verify" / "scripts"
)
sys.path.insert(0, str(_SKILL_SCRIPTS))


# ── helpers.is_ui_test ────────────────────────────────────────────────────────

from helpers import is_ui_test, matches_tc_filter


class TestIsUiTest:
    """is_ui_test returns True when any step contains a UI interaction keyword."""

    @pytest.mark.parametrize("steps,expected", [
        (["click the Submit button"], True),
        (["navigate to the model catalog page"], True),
        (["filter models by task type"], True),
        (["scroll down to load more results"], True),
        (["verify the checkbox is visible in the sidebar"], True),
        (["open the browser dashboard"], True),
        # Pure backend / API steps — no UI keywords
        (["run oc apply -f manifest.yaml"], False),
        (["call the API endpoint and verify 200"], False),
        (["ingest a model via the CLI"], False),
        ([], False),
    ])
    def test_ui_keyword_detection(self, steps, expected):
        assert is_ui_test(steps) == expected

    def test_case_insensitive(self):
        assert is_ui_test(["CLICK the BUTTON"])
        assert is_ui_test(["Navigate to HOME"])

    def test_match_on_any_step(self):
        """Only one step needs to contain a UI keyword."""
        assert is_ui_test([
            "ingest a model via the API",       # no keyword
            "click Validate to confirm",         # keyword here
        ])

    def test_keyword_embedded_mid_sentence(self):
        assert is_ui_test(["verify the filter sidebar renders correctly"])


# ── helpers.matches_tc_filter ─────────────────────────────────────────────────

class TestMatchesTcFilter:
    """matches_tc_filter supports exact IDs and category prefixes."""

    def test_empty_patterns_matches_everything(self):
        assert matches_tc_filter("TC-FILTER-001", [])
        assert matches_tc_filter("TC-E2E-099", [])

    @pytest.mark.parametrize("tc_id,patterns,expected", [
        # Exact match
        ("TC-FILTER-001", ["TC-FILTER-001"], True),
        ("TC-FILTER-002", ["TC-FILTER-001"], False),
        # Category prefix
        ("TC-FILTER-001", ["TC-FILTER"], True),
        ("TC-FILTER-042", ["TC-FILTER"], True),
        # Prefix requires dash separator — partial word must not match
        ("TC-FILTERX-001", ["TC-FILTER"], False),
        # Multiple patterns — any match wins
        ("TC-E2E-001", ["TC-FILTER", "TC-E2E"], True),
        ("TC-FILTER-003", ["TC-FILTER", "TC-E2E"], True),
        ("TC-CARD-001", ["TC-FILTER", "TC-E2E"], False),
        # Mixed exact + prefix
        ("TC-FILTER-001", ["TC-E2E-001", "TC-FILTER"], True),
    ])
    def test_filter_matching(self, tc_id, patterns, expected):
        assert matches_tc_filter(tc_id, patterns) == expected


# ── build_element_map.classify_file ──────────────────────────────────────────

from build_element_map import classify_file


class TestClassifyFile:
    """classify_file maps file paths to dashboard section names."""

    @pytest.mark.parametrize("filepath,expected_section", [
        # Pipelines
        ("src/pages/pipelines/GlobalPipelinesTable.tsx", "pipelines"),
        ("src/concepts/pipelines/PipelineRunDetails.tsx", "pipelines"),
        # Projects / data science
        ("src/pages/projects/ProjectDetails.tsx", "projects"),
        ("src/concepts/projects/ProjectCard.tsx", "projects"),
        # Model serving / deployments
        ("src/pages/modelServing/ModelServingRoutes.tsx", "model-serving"),
        # Workbenches / notebooks
        ("src/pages/notebookController/NotebookCard.tsx", "workbenches"),
        # Cluster settings
        ("src/pages/clusterSettings/ClusterSettings.tsx", "cluster-settings"),
        ("src/pages/settings/StorageClasses.tsx", "cluster-settings"),
        # Model catalog / AI hub
        ("src/pages/modelCatalog/CatalogPage.tsx", "catalog"),
        ("src/pages/aiHub/AiHubRoutes.tsx", "catalog"),
        # Unknown → falls back to "general"
        ("src/utils/someRandomUtil.ts", "general"),
        ("src/components/shared/Button.tsx", "general"),
    ])
    def test_section_classification(self, filepath, expected_section):
        assert classify_file(filepath) == expected_section


# ── ui_assert.update_log ─────────────────────────────────────────────────────

# ui_assert.py imports playwright at module level (exits if missing).
# Stub the playwright module so it can be imported in the test environment.
from unittest.mock import MagicMock
import sys as _sys
_pw_stub = MagicMock()
_pw_stub.sync_api.TimeoutError = TimeoutError  # map to built-in for isinstance checks
_sys.modules.setdefault("playwright", _pw_stub)
_sys.modules.setdefault("playwright.sync_api", _pw_stub.sync_api)

import ui_assert as _ua


class TestUpdateLog:
    """update_log writes assertions and maintains verdict priority."""

    def _run(self, monkeypatch, tmp_path, tc_id, what, expected, result, detail,
             replace=False):
        """Helper: redirect TC_LOG to tmp_path, call update_log, return parsed log."""
        log_path = tmp_path / "ui_tc_log.json"
        monkeypatch.setattr(_ua, "TC_LOG", log_path)
        _ua.update_log(tc_id, what, expected, result, detail, replace=replace)
        return json.loads(log_path.read_text())

    def test_creates_entry_on_first_write(self, monkeypatch, tmp_path):
        log = self._run(monkeypatch, tmp_path, "TC-001", "filter visible", "visible", "PASS", "found")
        assert "TC-001" in log
        assert log["TC-001"]["verdict"] == "PASS"
        assert len(log["TC-001"]["assertions"]) == 1

    def test_fail_overrides_pass(self, monkeypatch, tmp_path):
        self._run(monkeypatch, tmp_path, "TC-001", "er1", "ok", "PASS", "found")
        log = self._run(monkeypatch, tmp_path, "TC-001", "er2", "ok", "FAIL", "missing")
        assert log["TC-001"]["verdict"] == "FAIL"

    def test_pass_cannot_override_fail(self, monkeypatch, tmp_path):
        self._run(monkeypatch, tmp_path, "TC-001", "er1", "ok", "FAIL", "missing")
        log = self._run(monkeypatch, tmp_path, "TC-001", "er2", "ok", "PASS", "found")
        assert log["TC-001"]["verdict"] == "FAIL"

    def test_blocked_between_pass_and_fail(self, monkeypatch, tmp_path):
        self._run(monkeypatch, tmp_path, "TC-001", "er1", "ok", "PASS", "found")
        log = self._run(monkeypatch, tmp_path, "TC-001", "er2", "ok", "BLOCKED", "no backend")
        assert log["TC-001"]["verdict"] == "BLOCKED"

    @pytest.mark.parametrize("results,expected_verdict", [
        (["PASS", "PASS", "PASS"], "PASS"),
        (["PASS", "FAIL"], "FAIL"),
        (["PASS", "BLOCKED"], "BLOCKED"),
        (["BLOCKED", "FAIL"], "FAIL"),
        (["PASS", "PASS", "BLOCKED", "FAIL"], "FAIL"),
    ])
    def test_verdict_priority(self, monkeypatch, tmp_path, results, expected_verdict):
        log_path = tmp_path / "ui_tc_log.json"
        monkeypatch.setattr(_ua, "TC_LOG", log_path)
        for i, r in enumerate(results):
            _ua.update_log("TC-001", f"er{i}", "ok", r, "detail")
        log = json.loads(log_path.read_text())
        assert log["TC-001"]["verdict"] == expected_verdict

    def test_replace_removes_previous_entry_for_same_what(self, monkeypatch, tmp_path):
        self._run(monkeypatch, tmp_path, "TC-001", "filter visible", "ok", "FAIL", "not found")
        log = self._run(monkeypatch, tmp_path, "TC-001", "filter visible", "ok", "PASS", "found",
                        replace=True)
        # Ghost FAIL is gone, only the PASS remains
        assertions = log["TC-001"]["assertions"]
        assert all(a["result"] == "PASS" for a in assertions)
        assert log["TC-001"]["verdict"] == "PASS"

    def test_replace_preserves_other_assertions(self, monkeypatch, tmp_path):
        self._run(monkeypatch, tmp_path, "TC-001", "er1", "ok", "PASS", "found")
        self._run(monkeypatch, tmp_path, "TC-001", "er2", "ok", "FAIL", "missing")
        log = self._run(monkeypatch, tmp_path, "TC-001", "er2", "ok", "PASS", "now found",
                        replace=True)
        assertions = log["TC-001"]["assertions"]
        assert len(assertions) == 2
        assert log["TC-001"]["verdict"] == "PASS"

    def test_incomplete_verdict_not_overridden_by_pass(self, monkeypatch, tmp_path):
        """INCOMPLETE set at TC level must survive a passing assertion."""
        log_path = tmp_path / "ui_tc_log.json"
        monkeypatch.setattr(_ua, "TC_LOG", log_path)
        # Simulate INCOMPLETE being set by ui_block.py --incomplete
        log_path.write_text(json.dumps({
            "TC-001": {"title": "TC-001", "verdict": "INCOMPLETE",
                       "assertions": [], "blocked_reason": "crashed"}
        }))
        _ua.update_log("TC-001", "er1", "ok", "PASS", "found")
        log = json.loads(log_path.read_text())
        assert log["TC-001"]["verdict"] == "INCOMPLETE"

    def test_multiple_tcs_are_independent(self, monkeypatch, tmp_path):
        self._run(monkeypatch, tmp_path, "TC-001", "er1", "ok", "PASS", "found")
        self._run(monkeypatch, tmp_path, "TC-002", "er1", "ok", "FAIL", "missing")
        log_path = tmp_path / "ui_tc_log.json"
        log = json.loads(log_path.read_text())
        assert log["TC-001"]["verdict"] == "PASS"
        assert log["TC-002"]["verdict"] == "FAIL"
