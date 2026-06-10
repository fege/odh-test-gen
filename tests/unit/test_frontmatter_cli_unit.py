"""
Unit test for frontmatter CLI - simple test to increase coverage.
"""

import sys
from io import StringIO

import pytest

from scripts import frontmatter


def test_schema_command_output():
    """Test that schema command prints YAML output."""
    # Mock sys.argv for schema command
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ['frontmatter.py', 'schema', 'test-plan']
        sys.stdout = StringIO()

        # This should not raise
        try:
            frontmatter.main()
        except SystemExit as e:
            # Schema command exits with 0
            assert e.code == 0

        output = sys.stdout.getvalue()

        # Should print YAML schema
        assert 'required:' in output

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_set_version_field_rejected():
    """Setting version via frontmatter.py should exit 1 with redirect message."""
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ['frontmatter.py', 'set', 'TestPlan.md', 'version=2.0.0']
        sys.stdout = StringIO()

        with pytest.raises(SystemExit) as exc_info:
            frontmatter.main()
        assert exc_info.value.code == 1
    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
