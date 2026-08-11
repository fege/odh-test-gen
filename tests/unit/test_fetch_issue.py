"""
Unit tests for scripts/fetch_issue.py

Tests Jira issue markdown formatting logic.
"""

import pytest

from scripts.fetch_issue import format_issue_as_markdown, parse_components


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
            },
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
            },
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
                "components": [{"name": "Backend"}, {"name": "API"}],
            },
        }

        result = format_issue_as_markdown(issue_data)

        assert "- **Components**: Backend, API" in result

    def test_issue_with_missing_fields(self):
        """Test formatting issue with missing optional fields."""
        issue_data = {"key": "TEST-123", "fields": {}}

        result = format_issue_as_markdown(issue_data)

        assert "# TEST-123: No summary" in result
        assert "No description provided" in result
        assert "- **Type**: Unknown" in result
        assert "- **Status**: Unknown" in result


class TestParseComponents:
    """Tests for parse_components — the inverse of format_issue_as_markdown's Components bullet,
    used by test-plan-create to extract components from a saved strategy snapshot without an LLM
    reading and eyeballing the file.
    """

    @pytest.mark.parametrize(
        "components,expected",
        [
            ([{"name": "AI Hub"}, {"name": "Model Serving"}], ["AI Hub", "Model Serving"]),
            ([{"name": "AI Hub"}], ["AI Hub"]),
            ([], []),
        ],
    )
    def test_round_trips_with_format_issue_as_markdown(self, components, expected):
        issue_data = {"key": "TEST-123", "fields": {"components": components}}

        markdown = format_issue_as_markdown(issue_data)

        assert parse_components(markdown) == expected

    def test_ignores_components_bullet_in_description(self):
        issue_data = {
            "key": "TEST-123",
            "fields": {
                "components": [],
                "description": "Some description text\n- **Components**: Fake, Injected",
            },
        }

        markdown = format_issue_as_markdown(issue_data)

        assert parse_components(markdown) == []
