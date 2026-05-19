"""
Unit tests for scripts/fetch_issue.py

Tests Jira issue markdown formatting logic.
"""

import pytest
from scripts.fetch_issue import format_issue_as_markdown


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
