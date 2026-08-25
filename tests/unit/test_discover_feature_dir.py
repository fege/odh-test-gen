"""Unit tests for scripts/discover_feature_dir.py (RHAIFIRST-580).

`.test-plan-output-dir.json` is the single source of truth for a feature directory's saved
output-dir metadata (written unconditionally by `/test-plan-create` via
`parse_strat.py save-snapshot`). This script just reads and validates that marker file for a
given feature directory — no settings.json scanning, no multi-candidate/ambiguous logic.
"""

import io
import json

import pytest

from scripts.discover_feature_dir import discover_feature_dir, main
from scripts.parse_strat import OUTPUT_DIR_MARKER


def _write_marker(feature_dir, content: str):
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / OUTPUT_DIR_MARKER).write_text(content)


class TestDiscoverFeatureDirCore:
    """Direct calls to discover_feature_dir(feature_dir)."""

    @pytest.mark.parametrize(
        "marker_payload",
        [
            {"output_dir": "<tmp_path>"},
            {"output_dir": "<tmp_path>", "future_field": "value"},
        ],
        ids=["minimal-marker", "with-extra-metadata"],
    )
    def test_valid_marker_returns_contents(self, tmp_path, marker_payload):
        feature_dir = tmp_path / "nemo_guardrails"
        payload = {k: (str(tmp_path) if v == "<tmp_path>" else v) for k, v in marker_payload.items()}
        _write_marker(feature_dir, json.dumps(payload))

        assert discover_feature_dir(str(feature_dir)) == payload

    @pytest.mark.parametrize(
        "dir_name,dir_exists,marker_content",
        [
            ("no_marker_here", True, None),
            ("does_not_exist", False, None),
            ("nemo_guardrails", True, "{not valid json"),
            ("nemo_guardrails", True, "[]"),
            ("nemo_guardrails", True, "null"),
            ("nemo_guardrails", True, '"not-an-object"'),
        ],
        ids=[
            "missing-marker-file",
            "missing-feature-dir",
            "malformed-marker-json",
            "marker-json-array",
            "marker-json-null",
            "marker-json-string",
        ],
    )
    def test_discover_invalid_raises_error(self, tmp_path, dir_name, dir_exists, marker_content):
        feature_dir = tmp_path / dir_name

        if dir_exists:
            feature_dir.mkdir()
            if marker_content is not None:
                _write_marker(feature_dir, marker_content)

        with pytest.raises(ValueError):
            discover_feature_dir(str(feature_dir))

    def test_marker_missing_expected_keys_is_returned_as_is(self, tmp_path):
        feature_dir = tmp_path / "nemo_guardrails"
        _write_marker(feature_dir, json.dumps({"unexpected": "shape"}))

        assert discover_feature_dir(str(feature_dir)) == {"unexpected": "shape"}


class TestDiscoverFeatureDirCli:
    """CLI entry point via the run_cli fixture (tests/conftest.py): positional arg, stdin
    fallback, and exit-code behavior on missing/malformed input.
    """

    @pytest.mark.parametrize(
        "use_stdin",
        [False, True],
        ids=["positional-arg", "stdin-when-no-arg"],
    )
    def test_cli_prints_marker_contents(self, tmp_path, run_cli, monkeypatch, use_stdin):
        feature_dir = tmp_path / "nemo_guardrails"
        _write_marker(feature_dir, json.dumps({"output_dir": str(tmp_path)}))

        if use_stdin:
            monkeypatch.setattr("sys.stdin", io.StringIO(str(feature_dir) + "\n"))
            args = []
        else:
            args = [str(feature_dir)]

        exit_code, output = run_cli(main, args)

        assert exit_code == 0
        assert output == {"output_dir": str(tmp_path)}

    @pytest.mark.parametrize(
        "dir_name,marker_content,expected_error",
        [
            ("no_marker_here", None, "invalid_output_dir_marker"),
            ("nemo_guardrails", "{not valid json", "invalid_output_dir_marker"),
            ("nemo_guardrails", "[]", "invalid_output_dir_marker"),
            ("nemo_guardrails", "null", "invalid_output_dir_marker"),
            ("nemo_guardrails", '"not-an-object"', "invalid_output_dir_marker"),
        ],
        ids=[
            "missing-marker-file",
            "malformed-marker-json",
            "marker-json-array",
            "marker-json-null",
            "marker-json-string",
        ],
    )
    def test_cli_invalid_marker_error(self, tmp_path, run_cli, dir_name, marker_content, expected_error):
        feature_dir = tmp_path / dir_name
        if marker_content is None:
            feature_dir.mkdir()
        else:
            _write_marker(feature_dir, marker_content)

        exit_code, output = run_cli(main, [str(feature_dir)])

        assert exit_code == 1
        assert output["error"] == expected_error

    def test_cli_missing_feature_dir_arg_error(self, run_cli, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO(""))

        exit_code, output = run_cli(main, [])

        assert exit_code == 1
        assert output["error"] == "missing_feature_dir"
