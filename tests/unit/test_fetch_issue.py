"""
Tests for fetch_issue script.

These tests mock API responses and verify markdown output formatting.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from scripts.fetch_issue import format_issue_as_markdown, main


class TestFormatIssueAsMarkdown:
    """Tests for format_issue_as_markdown function."""

    def test_basic_issue_formatting(self):
        """Test formatting a basic issue."""
        issue_data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test issue summary",
                "description": "Test description",
                "issuetype": {"name": "Story"},
                "status": {"name": "In Progress"},
                "labels": [],
                "components": [],
            }
        }

        result = format_issue_as_markdown(issue_data)

        assert "# TEST-123: Test issue summary" in result
        assert "- **Type**: Story" in result
        assert "- **Status**: In Progress" in result
        assert "## Description" in result
        assert "Test description" in result

    def test_issue_with_labels(self):
        """Test formatting issue with labels."""
        issue_data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test",
                "description": "Desc",
                "issuetype": {"name": "Task"},
                "status": {"name": "Done"},
                "labels": ["bug", "frontend"],
                "components": [],
            }
        }

        result = format_issue_as_markdown(issue_data)

        assert "- **Labels**: bug, frontend" in result

    def test_issue_with_components(self):
        """Test formatting issue with components."""
        issue_data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test",
                "description": "Desc",
                "issuetype": {"name": "Bug"},
                "status": {"name": "Open"},
                "labels": [],
                "components": [
                    {"name": "Backend"},
                    {"name": "API"}
                ],
            }
        }

        result = format_issue_as_markdown(issue_data)

        assert "- **Components**: Backend, API" in result

    def test_issue_with_missing_fields(self):
        """Test formatting issue with missing optional fields."""
        issue_data = {
            "key": "TEST-123",
            "fields": {}
        }

        result = format_issue_as_markdown(issue_data)

        assert "# TEST-123: No summary" in result
        assert "No description provided" in result
        assert "- **Type**: Unknown" in result
        assert "- **Status**: Unknown" in result


class TestMain:
    """Tests for main CLI function."""

    @patch("scripts.fetch_issue.get_issue")
    @patch("builtins.print")
    def test_main_stdout_output(self, mock_print, mock_get_issue):
        """Test output to stdout when no file specified."""
        mock_get_issue.return_value = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test",
                "description": "Desc",
                "issuetype": {"name": "Task"},
                "status": {"name": "Open"},
                "labels": [],
                "components": [],
            }
        }

        with patch("sys.argv", ["fetch_issue.py", "TEST-123"]):
            main()

        # Should print markdown to stdout
        assert mock_print.called
        output = mock_print.call_args[0][0]
        assert "# TEST-123" in output

    @patch("scripts.fetch_issue.get_issue")
    @patch("builtins.open", new_callable=mock_open)
    @patch("builtins.print")
    def test_main_file_output(self, mock_print, mock_file, mock_get_issue):
        """Test output to file when specified."""
        mock_get_issue.return_value = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test",
                "description": "Desc",
                "issuetype": {"name": "Task"},
                "status": {"name": "Open"},
                "labels": [],
                "components": [],
            }
        }

        with patch("sys.argv", ["fetch_issue.py", "TEST-123", "--output", "test.md"]):
            main()

        # Should write to file
        mock_file.assert_called_once_with("test.md", "w")
        handle = mock_file()
        assert handle.write.called

    @patch("scripts.fetch_issue.get_issue")
    def test_main_with_fields_arg(self, mock_get_issue):
        """Test that fields argument is passed correctly."""
        mock_get_issue.return_value = {
            "key": "TEST-123",
            "fields": {"summary": "Test"}
        }

        with patch("sys.argv", ["fetch_issue.py", "TEST-123", "--fields", "summary,labels"]):
            main()

        mock_get_issue.assert_called_once_with("TEST-123", fields="summary,labels")

    @patch("scripts.fetch_issue.get_issue")
    @patch("sys.exit")
    def test_main_handles_errors(self, mock_exit, mock_get_issue):
        """Test that errors are handled gracefully."""
        mock_get_issue.side_effect = Exception("API error")

        with patch("sys.argv", ["fetch_issue.py", "TEST-123"]):
            main()

        mock_exit.assert_called_once_with(1)
