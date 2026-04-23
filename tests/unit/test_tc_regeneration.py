"""Unit tests for scripts/tc_regeneration.py"""

import json
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts import tc_regeneration


class TestTCRegenerationCheck:
    """Tests for tc_regeneration.py check command."""

    def test_create_mode_no_test_cases_dir(self):
        """Returns create mode when test_cases directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = Path(tmpdir)

            old_argv = sys.argv
            old_stdout = sys.stdout

            try:
                sys.argv = ['tc_regeneration.py', 'check', str(feature_dir)]
                sys.stdout = StringIO()

                exit_code = tc_regeneration.main()
                assert exit_code == 0

                output = sys.stdout.getvalue().strip()
                result = json.loads(output)

                assert result['mode'] == 'create'
                assert result['existing_count'] == 0
                assert result['files'] == []

            finally:
                sys.argv = old_argv
                sys.stdout = old_stdout

    def test_create_mode_empty_test_cases_dir(self):
        """Returns create mode when test_cases directory exists but is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = Path(tmpdir)
            test_cases_dir = feature_dir / "test_cases"
            test_cases_dir.mkdir()

            old_argv = sys.argv
            old_stdout = sys.stdout

            try:
                sys.argv = ['tc_regeneration.py', 'check', str(feature_dir)]
                sys.stdout = StringIO()

                exit_code = tc_regeneration.main()
                assert exit_code == 0

                output = sys.stdout.getvalue().strip()
                result = json.loads(output)

                assert result['mode'] == 'create'
                assert result['existing_count'] == 0
                assert result['files'] == []

            finally:
                sys.argv = old_argv
                sys.stdout = old_stdout

    def test_regenerate_mode_with_existing_tcs(self):
        """Returns regenerate mode when TC files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = Path(tmpdir)
            test_cases_dir = feature_dir / "test_cases"
            test_cases_dir.mkdir()

            # Create some TC files
            (test_cases_dir / "TC-API-001.md").write_text("# TC-API-001\n")
            (test_cases_dir / "TC-API-002.md").write_text("# TC-API-002\n")
            (test_cases_dir / "TC-E2E-001.md").write_text("# TC-E2E-001\n")

            old_argv = sys.argv
            old_stdout = sys.stdout

            try:
                sys.argv = ['tc_regeneration.py', 'check', str(feature_dir)]
                sys.stdout = StringIO()

                exit_code = tc_regeneration.main()
                assert exit_code == 0

                output = sys.stdout.getvalue().strip()
                result = json.loads(output)

                assert result['mode'] == 'regenerate'
                assert result['existing_count'] == 3
                assert len(result['files']) == 3
                assert all('TC-' in f for f in result['files'])

            finally:
                sys.argv = old_argv
                sys.stdout = old_stdout
