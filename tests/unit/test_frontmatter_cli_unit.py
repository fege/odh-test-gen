"""
Unit test for frontmatter CLI - simple test to increase coverage.
"""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path

import pytest

from scripts import frontmatter
from scripts.utils.frontmatter_utils import write_frontmatter
from tests.constants import VALID_TEST_GAPS_DATA, VALID_TEST_PLAN_DATA, VALID_TEST_PLAN_REVIEW_DATA


class TestReadFieldArgument:
    """Test that `frontmatter.py read <file> <field>` returns a single value."""

    @pytest.fixture()
    def test_plan_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "TestPlan.md"
            write_frontmatter(path, VALID_TEST_PLAN_DATA, "test-plan")
            yield str(path)

    def test_read_single_field_returns_value(self, test_plan_file):
        old_argv = sys.argv
        old_stdout = sys.stdout
        try:
            sys.argv = ["frontmatter.py", "read", test_plan_file, "source_key"]
            sys.stdout = StringIO()
            frontmatter.main()
            output = sys.stdout.getvalue().strip()
            assert output == "RHAISTRAT-400"
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout

    def test_read_nonexistent_field_exits_nonzero(self, test_plan_file):
        old_argv = sys.argv
        try:
            sys.argv = [
                "frontmatter.py",
                "read",
                test_plan_file,
                "no_such_field",
            ]
            with pytest.raises(SystemExit) as exc_info:
                frontmatter.main()
            assert exc_info.value.code == 1
        finally:
            sys.argv = old_argv

    def test_read_without_field_returns_all_json(self, test_plan_file):
        old_argv = sys.argv
        old_stdout = sys.stdout
        try:
            sys.argv = ["frontmatter.py", "read", test_plan_file]
            sys.stdout = StringIO()
            frontmatter.main()
            output = sys.stdout.getvalue()
            data = json.loads(output)
            assert data["source_key"] == "RHAISTRAT-400"
            assert data["feature"] == "Test Feature"
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout


# Every (schema, filename, field) combination used by skills.
# If a skill calls `frontmatter.py read <file> <field>`, it must appear here.
SKILL_READ_FIELD_CALLS = [
    ("test-plan", "TestPlan.md", VALID_TEST_PLAN_DATA, "source_key", "RHAISTRAT-400"),
    ("test-plan-review", "TestPlanReview.md", VALID_TEST_PLAN_REVIEW_DATA, "verdict", "Ready"),
    ("test-plan-review", "TestPlanReview.md", VALID_TEST_PLAN_REVIEW_DATA, "auto_revised", "False"),
]


class TestSkillFrontmatterReadCalls:
    """Verify every frontmatter.py read <file> <field> used by skills works."""

    @pytest.mark.parametrize(
        "schema_type,filename,data,field,expected",
        SKILL_READ_FIELD_CALLS,
        ids=[f"{s}:{f}" for s, _, _, f, _ in SKILL_READ_FIELD_CALLS],
    )
    def test_skill_read_field(self, schema_type, filename, data, field, expected):
        old_argv = sys.argv
        old_stdout = sys.stdout
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / filename
                write_frontmatter(path, data, schema_type)
                sys.argv = ["frontmatter.py", "read", str(path), field]
                sys.stdout = StringIO()
                frontmatter.main()
                output = sys.stdout.getvalue().strip()
                assert output == expected
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout


def test_schema_command_output():
    """Test that schema command prints YAML output."""
    # Mock sys.argv for schema command
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ["frontmatter.py", "schema", "test-plan"]
        sys.stdout = StringIO()

        # This should not raise
        try:
            frontmatter.main()
        except SystemExit as e:
            # Schema command exits with 0
            assert e.code == 0

        output = sys.stdout.getvalue()

        # Should print YAML schema
        assert "required:" in output

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_set_version_field_rejected():
    """Setting version via frontmatter.py should exit 1 with redirect message."""
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ["frontmatter.py", "set", "TestPlan.md", "version=2.0.0"]
        sys.stdout = StringIO()

        with pytest.raises(SystemExit) as exc_info:
            frontmatter.main()
        assert exc_info.value.code == 1
    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_set_oserror_emits_structured_json(monkeypatch, capsys, tmp_path):
    """Filesystem failures from atomic writers must not dump a traceback."""
    path = tmp_path / "TestPlan.md"
    write_frontmatter(path, VALID_TEST_PLAN_DATA, "test-plan")

    def boom(*_args, **_kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr(frontmatter, "update_frontmatter", boom)
    monkeypatch.setattr(
        sys,
        "argv",
        ["frontmatter.py", "set", str(path), "status=Draft"],
    )

    with pytest.raises(SystemExit) as exc_info:
        frontmatter.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "replace failed" in captured.err
    assert "Traceback (most recent call last):" not in captured.err
    assert json.loads(captured.out) == {"status": "failed", "error": "write_failed"}


def test_set_invalid_coerce_emits_structured_json(monkeypatch, capsys, tmp_path):
    """Bad typed field values must not dump a traceback from int()/bool parsing."""
    path = tmp_path / "TestPlanGaps.md"
    write_frontmatter(path, VALID_TEST_GAPS_DATA, "test-gaps")
    monkeypatch.setattr(
        sys,
        "argv",
        ["frontmatter.py", "set", str(path), "gap_count=abc"],
    )

    with pytest.raises(SystemExit) as exc_info:
        frontmatter.main()

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.err
    assert json.loads(captured.out) == {"status": "failed", "error": "invalid_field_value"}
