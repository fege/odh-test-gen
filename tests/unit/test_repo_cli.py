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


def test_locate_feature_dir_local_path():
    """Test locate-feature-dir with local directory path."""
    old_argv = sys.argv
    old_stdout = sys.stdout

    try:
        sys.argv = ['repo.py', 'locate-feature-dir', '/tmp/test-validation/mcp_catalog']
        sys.stdout = StringIO()

        with patch('os.path.isfile') as mock_isfile:
            mock_isfile.return_value = True  # TestPlan.md exists

            try:
                repo.main()
            except SystemExit as e:
                assert e.code == 0

            output = sys.stdout.getvalue().strip()

            # Should be valid JSON
            result = json.loads(output)
            assert result['feature_dir'] == '/tmp/test-validation/mcp_catalog'
            assert result['source_type'] == 'local'
            assert 'repo_owner' not in result  # local paths don't have repo info

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout


def test_locate_feature_dir_github_pr():
    """Test locate-feature-dir with GitHub PR URL."""
    old_argv = sys.argv
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        sys.argv = ['repo.py', 'locate-feature-dir', 'https://github.com/org/repo/pull/42']
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        with patch('subprocess.run') as mock_run, \
             patch('scripts.utils.repo_utils.find_repo_in_common_locations') as mock_find, \
             patch('scripts.repo._find_testplan_in_repo') as mock_testplan:

            # Mock gh pr view to return branch name
            mock_run.return_value.stdout = '{"headRefName": "test-plan/RHAISTRAT-400"}'
            mock_run.return_value.returncode = 0

            # Mock repo found locally
            mock_find.return_value = '/Users/test/Code/repo'

            # Mock TestPlan.md found
            mock_testplan.return_value = '/Users/test/Code/repo/mcp_catalog'

            try:
                repo.main()
            except SystemExit as e:
                assert e.code == 0

            output = sys.stdout.getvalue().strip()

            # Should be valid JSON
            result = json.loads(output)
            assert result['source_type'] == 'github'
            assert result['repo_owner'] == 'org'
            assert result['repo_name'] == 'repo'
            assert 'feature_dir' in result

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def test_locate_feature_dir_missing_testplan():
    """Test locate-feature-dir fails when TestPlan.md doesn't exist."""
    old_argv = sys.argv
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        sys.argv = ['repo.py', 'locate-feature-dir', '/tmp/nonexistent']
        sys.stdout = StringIO()
        sys.stderr = StringIO()

        with patch('os.path.isfile') as mock_isfile:
            mock_isfile.return_value = False  # TestPlan.md doesn't exist

            try:
                exit_code = repo.main()
                assert exit_code == 1
            except SystemExit as e:
                assert e.code == 1

            error_output = sys.stderr.getvalue()
            assert 'TestPlan.md not found' in error_output

    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr
