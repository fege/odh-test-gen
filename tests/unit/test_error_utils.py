"""Unit tests for scripts.utils.error_utils exit helpers."""

import json

import pytest

from scripts.utils.error_utils import (
    exit_error,
    exit_error_multiline,
    exit_error_with_json,
    exit_graceful,
)


class TestExitError:
    def test_prints_message_to_stderr_and_exits_1(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            exit_error("boom")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.err == "boom\n"
        assert captured.out == ""

    def test_rejects_unexpected_kwargs(self):
        """Call sites must not pass print()-style kwargs like file=sys.stderr."""
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            exit_error("boom", file=object())


class TestExitGraceful:
    def test_prints_message_to_stderr_and_exits_0(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            exit_graceful("soft fail")

        assert exc_info.value.code == 0
        assert capsys.readouterr().err == "soft fail\n"


class TestExitErrorMultiline:
    def test_prints_each_line_and_exits_1(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            exit_error_multiline(["one", "two"])

        assert exc_info.value.code == 1
        assert capsys.readouterr().err == "one\ntwo\n"


class TestExitErrorWithJson:
    def test_dict_only(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            exit_error_with_json({"status": "failed", "error": "no_labels"})

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.err == ""
        assert json.loads(captured.out) == {"status": "failed", "error": "no_labels"}

    def test_message_and_error_key(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            exit_error_with_json(message="human detail", error_key="write_failed", indent=None)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert captured.err == "human detail\n"
        assert json.loads(captured.out) == {"error": "write_failed"}

    def test_dict_plus_message(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            exit_error_with_json(
                {"status": "error", "error": "add_labels_failed"},
                message="Failed to add labels",
                indent=None,
            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to add labels" in captured.err
        assert json.loads(captured.out) == {"status": "error", "error": "add_labels_failed"}
