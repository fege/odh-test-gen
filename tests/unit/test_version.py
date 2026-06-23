"""Unit tests for scripts/version.py — version management CLI."""

import json
import sys
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

import pytest

from tests.constants import VALID_TEST_PLAN_DATA
from scripts import version
from scripts.version import bump_version
from scripts.utils.frontmatter_utils import write_frontmatter, read_frontmatter


def _create_test_plan(tmpdir, ver="1.0.0", body="# Test Plan\n\nBody content.\n"):
    """Create a TestPlan.md with given version in a temp directory."""
    path = Path(tmpdir) / "TestPlan.md"
    data = {**VALID_TEST_PLAN_DATA, "version": ver}
    write_frontmatter(str(path), data, "test-plan")
    with open(path, "a", encoding="utf-8") as f:
        f.write(body)
    return str(path)


def _write_raw_frontmatter(tmpdir, yaml_body):
    """Write a TestPlan.md with raw YAML frontmatter (no schema validation)."""
    path = Path(tmpdir) / "TestPlan.md"
    path.write_text(
        f"---\n{yaml_body}---\n# Body\n",
        encoding="utf-8",
    )
    return str(path)


class TestBumpVersion:
    """Unit tests for the bump_version function."""

    @pytest.mark.parametrize(
        "version_in,bump_type,expected",
        [
            ("1.0.0", "patch", "1.0.1"),
            ("1.2.3", "minor", "1.3.0"),
            ("1.2.3", "major", "2.0.0"),
        ],
    )
    def test_bump(self, version_in, bump_type, expected):
        assert bump_version(version_in, bump_type) == expected

    @pytest.mark.parametrize(
        "version_in,bump_type,error_match",
        [
            ("not-a-version", "patch", "Invalid semver"),
            ("1.0.0", "invalid", "Unknown bump type"),
        ],
    )
    def test_bump_raises(self, version_in, bump_type, error_match):
        with pytest.raises(ValueError, match=error_match):
            bump_version(version_in, bump_type)


class TestVersionFieldEdgeCases:
    """Tests for version field handling via CLI."""

    def test_falsy_version_not_treated_as_missing(self):
        """A falsy version value (e.g. 0) should not be rejected as missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_raw_frontmatter(
                tmpdir,
                (
                    "feature: Test Feature\n"
                    "source_key: RHAISTRAT-400\n"
                    "version: 0\n"
                    "status: Draft\n"
                    "last_updated: '2026-04-14'\n"
                    "author: QE Team\n"
                ),
            )

            ver, schema_type = version._read_current_version(path)
            assert ver == "0"
            assert schema_type == "test-plan"


class TestCmdSetErrorPaths:
    """Tests for cmd_set error handling."""

    def test_invalid_semver_exits(self):
        """set with a non-semver string should exit 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _create_test_plan(tmpdir)

            old_argv, old_stdout = sys.argv, sys.stdout
            try:
                sys.argv = ["version.py", "set", path, "not-a-version"]
                sys.stdout = StringIO()

                with pytest.raises(SystemExit) as exc_info:
                    version.main()
                assert exc_info.value.code == 1
            finally:
                sys.argv, sys.stdout = old_argv, old_stdout

    def test_same_version_signals_no_change(self):
        """set to the current version should exit 0 with no_change in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _create_test_plan(tmpdir, "1.0.0")

            old_argv, old_stdout = sys.argv, sys.stdout
            try:
                sys.argv = ["version.py", "set", path, "1.0.0"]
                sys.stdout = StringIO()

                with pytest.raises(SystemExit) as exc_info:
                    version.main()
                assert exc_info.value.code == 0

                result = json.loads(sys.stdout.getvalue())
                assert result["no_change"] is True
                assert result["old_version"] == "1.0.0"
            finally:
                sys.argv, sys.stdout = old_argv, old_stdout


class TestVersionCLI:
    """Tests for bump and set subcommands via CLI."""

    @pytest.mark.parametrize(
        "cli_args,expected_new",
        [
            (["bump", "PLACEHOLDER", "patch"], "1.0.1"),
            (["set", "PLACEHOLDER", "3.0.0"], "3.0.0"),
        ],
    )
    def test_outputs_json_and_updates_file(self, cli_args, expected_new):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _create_test_plan(tmpdir, "1.0.0")
            cli_args = [a if a != "PLACEHOLDER" else path for a in cli_args]

            old_argv = sys.argv
            old_stdout = sys.stdout

            try:
                sys.argv = ["version.py", *cli_args]
                sys.stdout = StringIO()

                try:
                    version.main()
                except SystemExit as e:
                    assert e.code == 0

                output = sys.stdout.getvalue()
                result = json.loads(output)
                assert result["old_version"] == "1.0.0"
                assert result["new_version"] == expected_new

                data, _ = read_frontmatter(path)
                assert data["version"] == expected_new
                assert data["last_updated"] == date.today().isoformat()

            finally:
                sys.argv = old_argv
                sys.stdout = old_stdout
