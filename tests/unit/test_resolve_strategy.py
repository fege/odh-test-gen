"""Unit tests for scripts/resolve_strategy.py — snapshot-primary strategy resolution shared by
test-plan-review and test-plan-score.

Mocks at the same boundary as test_jira_utils.py (api_call_with_retry) so get_issue and
format_issue_as_markdown run for real — resolve_strategy is exercised through its actual
dependencies, not a hand-built stand-in for what they return.
"""

import json
import sys
from unittest.mock import patch

import pytest
import requests

from scripts.resolve_strategy import main, resolve_strategy

# Stands in for what a real Jira error can contain — request URL, query params, server body —
# none of which should ever reach stdout/logs.
SENSITIVE_HTTP_ERROR = "500 Server Error: https://issues.example.com/rest/api/2/issue/RHAISTRAT-1746?token=abc123"


class TestResolveStrategy:
    @patch("scripts.jira_utils.api_call_with_retry")
    def test_snapshot_hit_returns_its_path_without_fetching(self, mock_api_call, tmp_path):
        snapshot = tmp_path / ".source-strategy.md"
        snapshot.write_text("# Cached strategy\n")

        result = resolve_strategy(str(tmp_path), "RHAISTRAT-1746")

        assert result == {"status": "ok", "source": "snapshot", "strategy_file": str(snapshot)}
        mock_api_call.assert_not_called()

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_refetch_on_missing_snapshot_saves_it(self, mock_api_call, tmp_path):
        mock_api_call.return_value = {
            "key": "RHAISTRAT-1746",
            "fields": {"summary": "Vector store registration"},
        }

        result = resolve_strategy(str(tmp_path), "RHAISTRAT-1746")

        snapshot = tmp_path / ".source-strategy.md"
        assert result == {"status": "ok", "source": "refetch", "strategy_file": str(snapshot)}
        assert "Vector store registration" in snapshot.read_text()

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_hard_fail_when_no_snapshot_and_fetch_fails(self, mock_api_call, tmp_path):
        mock_api_call.side_effect = requests.HTTPError(SENSITIVE_HTTP_ERROR)

        with pytest.raises(requests.HTTPError):
            resolve_strategy(str(tmp_path), "RHAISTRAT-1746")

        assert not (tmp_path / ".source-strategy.md").exists()

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_creates_feature_dir_if_missing_before_writing_snapshot(self, mock_api_call, tmp_path):
        mock_api_call.return_value = {
            "key": "RHAISTRAT-1746",
            "fields": {"summary": "Vector store registration"},
        }
        feature_dir = tmp_path / "not_yet_created"

        result = resolve_strategy(str(feature_dir), "RHAISTRAT-1746")

        snapshot = feature_dir / ".source-strategy.md"
        assert result == {"status": "ok", "source": "refetch", "strategy_file": str(snapshot)}
        assert "Vector store registration" in snapshot.read_text()

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_snapshot_write_failure_raises_oserror(self, mock_api_call, tmp_path):
        mock_api_call.return_value = {
            "key": "RHAISTRAT-1746",
            "fields": {"summary": "Vector store registration"},
        }
        # A plain file sitting where the feature directory should be: mkdir(exist_ok=True) still
        # raises for a non-directory occupant, exercising the write-failure path deterministically.
        blocked_feature_dir = tmp_path / "blocked"
        blocked_feature_dir.write_text("not a directory")

        with pytest.raises(OSError):
            resolve_strategy(str(blocked_feature_dir), "RHAISTRAT-1746")


class TestResolveStrategyCLI:
    @patch("scripts.jira_utils.api_call_with_retry")
    def test_ok_path_prints_status_ok_and_exits_zero(self, mock_api_call, tmp_path, capsys):
        mock_api_call.return_value = {
            "key": "RHAISTRAT-1746",
            "fields": {"summary": "Vector store registration"},
        }

        old_argv = sys.argv
        try:
            sys.argv = ["resolve_strategy.py", str(tmp_path), "RHAISTRAT-1746"]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit")
        finally:
            sys.argv = old_argv

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "ok"
        assert output["source"] == "refetch"

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_fetch_failure_exits_one_with_stable_error_code(self, mock_api_call, tmp_path, capsys):
        mock_api_call.side_effect = requests.HTTPError(SENSITIVE_HTTP_ERROR)

        old_argv = sys.argv
        try:
            sys.argv = ["resolve_strategy.py", str(tmp_path), "RHAISTRAT-1746"]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("main() must exit with code 1")
        finally:
            sys.argv = old_argv

        raw_output = capsys.readouterr().out
        output = json.loads(raw_output)
        assert output == {"status": "failed", "error": "jira_fetch_failed"}
        assert "issues.example.com" not in raw_output
        assert "token=abc123" not in raw_output

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_snapshot_write_failure_exits_one_with_stable_error_code(self, mock_api_call, tmp_path, capsys):
        mock_api_call.return_value = {
            "key": "RHAISTRAT-1746",
            "fields": {"summary": "Vector store registration"},
        }
        blocked_feature_dir = tmp_path / "blocked"
        blocked_feature_dir.write_text("not a directory")

        old_argv = sys.argv
        try:
            sys.argv = ["resolve_strategy.py", str(blocked_feature_dir), "RHAISTRAT-1746"]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("main() must exit with code 1")
        finally:
            sys.argv = old_argv

        assert json.loads(capsys.readouterr().out) == {"status": "failed", "error": "snapshot_write_failed"}


class TestResolveStrategySymlinkRejection:
    """Verify that resolve_strategy's is_symlink() guard rejects a pre-existing symlink at the
    snapshot path before any Jira fetch or write — both a regular-file symlink and a dangling
    symlink must raise OSError, mapped to snapshot_write_failed at the CLI level.
    (write_snapshot_nofollow's own O_NOFOLLOW backstop is covered in tests/unit/test_snapshot_io.py.)
    """

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_refetch_rejects_symlink_to_regular_file(self, mock_api_call, tmp_path):
        victim = tmp_path / "victim.md"
        victim.write_text("must not be overwritten")
        (tmp_path / ".source-strategy.md").symlink_to(victim)

        with pytest.raises(OSError, match="snapshot path is a symlink"):
            resolve_strategy(str(tmp_path), "RHAISTRAT-1746")

        assert victim.read_text() == "must not be overwritten"
        mock_api_call.assert_not_called()

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_refetch_rejects_dangling_symlink(self, mock_api_call, tmp_path):
        (tmp_path / ".source-strategy.md").symlink_to(tmp_path / "nonexistent.md")

        with pytest.raises(OSError, match="snapshot path is a symlink"):
            resolve_strategy(str(tmp_path), "RHAISTRAT-1746")

        assert not (tmp_path / "nonexistent.md").exists()
        mock_api_call.assert_not_called()

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_refetch_symlink_cli_exits_one_with_snapshot_write_failed(self, mock_api_call, tmp_path, capsys):
        mock_api_call.return_value = {
            "key": "RHAISTRAT-1746",
            "fields": {"summary": "Vector store registration"},
        }
        victim = tmp_path / "victim.md"
        victim.write_text("must not be overwritten")
        (tmp_path / ".source-strategy.md").symlink_to(victim)

        old_argv = sys.argv
        try:
            sys.argv = ["resolve_strategy.py", str(tmp_path), "RHAISTRAT-1746"]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("main() must exit with code 1")
        finally:
            sys.argv = old_argv

        assert json.loads(capsys.readouterr().out) == {"status": "failed", "error": "snapshot_write_failed"}
        assert victim.read_text() == "must not be overwritten"

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_refetch_dangling_symlink_cli_exits_one_with_snapshot_write_failed(self, mock_api_call, tmp_path, capsys):
        mock_api_call.return_value = {
            "key": "RHAISTRAT-1746",
            "fields": {"summary": "Vector store registration"},
        }
        (tmp_path / ".source-strategy.md").symlink_to(tmp_path / "nonexistent.md")

        old_argv = sys.argv
        try:
            sys.argv = ["resolve_strategy.py", str(tmp_path), "RHAISTRAT-1746"]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("main() must exit with code 1")
        finally:
            sys.argv = old_argv

        assert json.loads(capsys.readouterr().out) == {"status": "failed", "error": "snapshot_write_failed"}
