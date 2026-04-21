"""
Unit test for repo CLI - simple smoke test to ensure CLI interface is stable.
"""

import json
import sys
from io import StringIO
from unittest.mock import patch

from scripts import repo


def test_find_command_basic():
    """Test that find command works and returns path."""
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ['repo.py', 'find', 'test-plan']
        sys.stdout = StringIO()

        with patch('scripts.utils.repo_utils.find_repo_in_common_locations') as mock_find:
            mock_find.return_value = '/Users/test/Code/test-plan'

            # This should not raise
            try:
                repo.main()
            except SystemExit as e:
                # find command exits with 0 when found
                assert e.code == 0

            output = sys.stdout.getvalue().strip()

            # Should print path
            assert '/test-plan' in output

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_find_known_returns_json():
    """Test that find-known command returns JSON format."""
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ['repo.py', 'find-known', 'odh-test-context']
        sys.stdout = StringIO()

        with patch('scripts.utils.repo_utils.find_known_repo') as mock_find:
            mock_find.return_value = (
                '/Users/test/Code/odh-test-context',
                'https://github.com/opendatahub-io/odh-test-context'
            )

            try:
                repo.main()
            except SystemExit as e:
                assert e.code == 0

            output = sys.stdout.getvalue().strip()

            # Should be valid JSON
            result = json.loads(output)
            assert 'path' in result
            assert 'url' in result

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
