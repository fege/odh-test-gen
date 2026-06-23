"""
Unit tests for scripts/jira_utils.py

Tests Jira REST API client with retry logic, error handling,
and label merging. Mocks HTTP layer to avoid actual API calls.
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch
import requests
from scripts.jira_utils import (
    require_env,
    make_request,
    api_call,
    api_call_with_retry,
    get_issue,
    add_labels,
)


class TestRequireEnv:
    """Tests for require_env function."""

    def test_require_env_present(self):
        """Test that require_env returns value when set."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            assert require_env("TEST_VAR") == "test_value"

    def test_require_env_missing(self):
        """Test that require_env exits when variable is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit):
                require_env("MISSING_VAR")


class TestMakeRequest:
    """Tests for make_request function."""

    @patch("scripts.jira_utils.requests.request")
    def test_make_request_success(self, mock_request):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        env_vars = {
            "JIRA_URL": "https://jira.example.com",
            "JIRA_USER": "test_user",
            "JIRA_TOKEN": "test_token",
        }

        with patch.dict(os.environ, env_vars):
            response = make_request("GET", "/rest/api/2/issue/TEST-123")

        assert response == mock_response
        mock_request.assert_called_once()

    @patch("scripts.jira_utils.requests.request")
    def test_make_request_http_error(self, mock_request):
        """Test that HTTP errors are raised."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_request.return_value = mock_response

        env_vars = {
            "JIRA_URL": "https://jira.example.com",
            "JIRA_USER": "test_user",
            "JIRA_TOKEN": "test_token",
        }

        with patch.dict(os.environ, env_vars):
            with pytest.raises(requests.HTTPError):
                make_request("GET", "/rest/api/2/issue/MISSING-123")


class TestApiCall:
    """Tests for api_call function."""

    @patch("scripts.jira_utils.make_request")
    def test_api_call_returns_json(self, mock_make_request):
        """Test that api_call returns JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"key": "TEST-123"}'
        mock_response.json.return_value = {"key": "TEST-123", "fields": {}}
        mock_make_request.return_value = mock_response

        result = api_call("/rest/api/2/issue/TEST-123")

        assert result == {"key": "TEST-123", "fields": {}}
        mock_make_request.assert_called_once_with("GET", "/rest/api/2/issue/TEST-123", None, None)

    @patch("scripts.jira_utils.make_request")
    def test_api_call_handles_204_no_content(self, mock_make_request):
        """Test that api_call handles 204 No Content responses."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b""
        mock_make_request.return_value = mock_response

        result = api_call("/rest/api/2/issue/TEST-123", method="PUT")

        assert result is None

    @patch("scripts.jira_utils.make_request")
    def test_api_call_handles_empty_content(self, mock_make_request):
        """Test that api_call handles empty response content."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_make_request.return_value = mock_response

        result = api_call("/rest/api/2/issue/TEST-123")

        assert result is None


class TestApiCallWithRetry:
    """Tests for api_call_with_retry function."""

    @patch("scripts.jira_utils.api_call")
    def test_retry_success_first_attempt(self, mock_api_call):
        """Test successful call on first attempt."""
        mock_api_call.return_value = {"key": "TEST-123"}

        result = api_call_with_retry("/rest/api/2/issue/TEST-123")

        assert result == {"key": "TEST-123"}
        assert mock_api_call.call_count == 1

    @patch("scripts.jira_utils.api_call")
    @patch("scripts.jira_utils.time.sleep")
    def test_retry_success_after_failure(self, mock_sleep, mock_api_call):
        """Test successful call after transient 500 error."""
        mock_response = Mock()
        mock_response.status_code = 500

        # First call fails, second succeeds
        mock_api_call.side_effect = [requests.HTTPError(response=mock_response), {"key": "TEST-123"}]

        result = api_call_with_retry("/rest/api/2/issue/TEST-123", max_retries=3)

        assert result == {"key": "TEST-123"}
        assert mock_api_call.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("scripts.jira_utils.api_call")
    def test_no_retry_on_4xx_errors(self, mock_api_call):
        """Test that 4xx errors are not retried."""
        mock_response = Mock()
        mock_response.status_code = 404

        mock_api_call.side_effect = requests.HTTPError(response=mock_response)

        with pytest.raises(requests.HTTPError):
            api_call_with_retry("/rest/api/2/issue/MISSING-123", max_retries=3)

        # Should only try once for 4xx errors
        assert mock_api_call.call_count == 1

    @patch("scripts.jira_utils.api_call")
    @patch("builtins.print")
    def test_no_retry_on_auth_errors_with_message(self, mock_print, mock_api_call):
        """Test that auth errors (401, 403) are not retried and show helpful message."""
        for status_code in (401, 403):
            mock_print.reset_mock()
            mock_api_call.reset_mock()

            mock_response = Mock()
            mock_response.status_code = status_code
            mock_api_call.side_effect = requests.HTTPError(response=mock_response)

            with pytest.raises(requests.HTTPError):
                api_call_with_retry("/rest/api/2/issue/TEST-123", max_retries=3)

            # Should only try once for auth errors
            assert mock_api_call.call_count == 1

            # Should print helpful message to stderr
            stderr_calls = [call for call in mock_print.call_args_list if call.kwargs.get("file") == sys.stderr]
            assert stderr_calls
            error_msg = stderr_calls[0].args[0]
            assert "Authentication error" in error_msg or f"({status_code})" in error_msg
            assert "JIRA_" in error_msg  # Mentions env vars

    @patch("scripts.jira_utils.api_call")
    @patch("scripts.jira_utils.time.sleep")
    def test_retry_exhaustion(self, mock_sleep, mock_api_call):
        """Test that all retries are exhausted on persistent 500 error."""
        mock_response = Mock()
        mock_response.status_code = 500

        mock_api_call.side_effect = requests.HTTPError(response=mock_response)

        with pytest.raises(requests.HTTPError):
            api_call_with_retry("/rest/api/2/issue/TEST-123", max_retries=3)

        assert mock_api_call.call_count == 3
        assert mock_sleep.call_count == 2


class TestGetIssue:
    """Tests for get_issue function."""

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_get_issue_basic(self, mock_api_call):
        """Test basic issue fetch."""
        expected = {"key": "TEST-123", "fields": {"summary": "Test issue"}}
        mock_api_call.return_value = expected

        result = get_issue("TEST-123")

        assert result == expected
        mock_api_call.assert_called_once_with("/rest/api/2/issue/TEST-123", params={})

    @patch("scripts.jira_utils.api_call_with_retry")
    def test_get_issue_with_fields(self, mock_api_call):
        """Test issue fetch with field filter."""
        expected = {"key": "TEST-123", "fields": {"summary": "Test"}}
        mock_api_call.return_value = expected

        result = get_issue("TEST-123", fields="summary,labels")

        assert result == expected
        mock_api_call.assert_called_once_with("/rest/api/2/issue/TEST-123", params={"fields": "summary,labels"})


class TestAddLabels:
    """Tests for add_labels function."""

    @patch("scripts.jira_utils.api_call_with_retry")
    @patch("scripts.jira_utils.get_issue")
    def test_add_labels_to_empty(self, mock_get_issue, mock_api_call):
        """Test adding labels to issue with no existing labels."""
        mock_get_issue.return_value = {"key": "TEST-123", "fields": {"labels": []}}
        mock_api_call.return_value = None  # 204 No Content

        result = add_labels("TEST-123", ["new-label"])

        # Should return None (void function)
        assert result is None

        # Verify the update call
        mock_api_call.assert_called_once_with(
            "/rest/api/2/issue/TEST-123", method="PUT", json_data={"fields": {"labels": ["new-label"]}}
        )

    @patch("scripts.jira_utils.api_call_with_retry")
    @patch("scripts.jira_utils.get_issue")
    def test_add_labels_merge_existing(self, mock_get_issue, mock_api_call):
        """Test that new labels are merged with existing labels."""
        mock_get_issue.return_value = {"key": "TEST-123", "fields": {"labels": ["existing-label"]}}
        mock_api_call.return_value = None  # 204 No Content

        add_labels("TEST-123", ["new-label"])

        # Should contain both labels
        call_args = mock_api_call.call_args
        labels = call_args[1]["json_data"]["fields"]["labels"]
        assert set(labels) == {"existing-label", "new-label"}

    @patch("scripts.jira_utils.api_call_with_retry")
    @patch("scripts.jira_utils.get_issue")
    def test_add_labels_no_duplicates(self, mock_get_issue, mock_api_call):
        """Test that duplicate labels are not added."""
        mock_get_issue.return_value = {"key": "TEST-123", "fields": {"labels": ["existing-label"]}}
        mock_api_call.return_value = None  # 204 No Content

        add_labels("TEST-123", ["existing-label", "new-label"])

        # Should deduplicate
        call_args = mock_api_call.call_args
        labels = call_args[1]["json_data"]["fields"]["labels"]
        assert set(labels) == {"existing-label", "new-label"}
        assert len(labels) == 2

    @patch("scripts.jira_utils.api_call_with_retry")
    @patch("scripts.jira_utils.get_issue")
    def test_add_labels_preserves_order(self, mock_get_issue, mock_api_call):
        """Test that label order is deterministic (existing first, new appended)."""
        mock_get_issue.return_value = {"key": "TEST-123", "fields": {"labels": ["label-a", "label-b", "label-c"]}}
        mock_api_call.return_value = None  # 204 No Content

        add_labels("TEST-123", ["label-d", "label-e"])

        # Should preserve existing order and append new labels
        call_args = mock_api_call.call_args
        labels = call_args[1]["json_data"]["fields"]["labels"]
        assert labels == ["label-a", "label-b", "label-c", "label-d", "label-e"]

    @patch("scripts.jira_utils.api_call_with_retry")
    @patch("scripts.jira_utils.get_issue")
    def test_add_labels_skips_api_call_when_no_change(self, mock_get_issue, mock_api_call):
        """Test that no API call is made when all labels already exist."""
        mock_get_issue.return_value = {"key": "TEST-123", "fields": {"labels": ["existing-label", "another-label"]}}

        add_labels("TEST-123", ["existing-label"])

        # Should NOT call the update API (all labels already present)
        mock_api_call.assert_not_called()

    @patch("scripts.jira_utils.api_call_with_retry")
    @patch("scripts.jira_utils.get_issue")
    def test_add_labels_deterministic_order(self, mock_get_issue, mock_api_call):
        """Test that label order is deterministic (no set() randomness)."""
        mock_get_issue.return_value = {"key": "TEST-123", "fields": {"labels": ["z", "a", "m"]}}
        mock_api_call.return_value = None

        # Add labels
        add_labels("TEST-123", ["b", "y"])

        # Should preserve existing order and append new labels in given order
        call_args = mock_api_call.call_args
        labels = call_args[1]["json_data"]["fields"]["labels"]

        # Verify exact order (not set-based which would be random)
        assert labels == ["z", "a", "m", "b", "y"]
