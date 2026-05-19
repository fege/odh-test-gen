"""
Core utilities for interacting with the Jira REST API.

This module provides low-level API access functions with retry logic and error handling.
Environment variables:
- JIRA_URL: Base URL for the Jira instance (required)
- JIRA_USER: Username or email for authentication (required)
- JIRA_TOKEN: API token for authentication (required)
"""

import os
import sys
import time
from typing import Any, Dict, Optional
import requests


def require_env(var_name: str) -> str:
    """
    Require an environment variable to be set.

    Args:
        var_name: Name of the environment variable

    Returns:
        The value of the environment variable

    Raises:
        SystemExit: If the environment variable is not set
    """
    value = os.getenv(var_name)
    if not value:
        print(f"Error: {var_name} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return value


def make_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> requests.Response:
    """
    Make an HTTP request to the Jira API.

    Args:
        method: HTTP method (GET, POST, PUT, etc.)
        endpoint: API endpoint path (e.g., '/rest/api/2/issue/PROJ-123')
        json_data: Optional JSON body for the request
        params: Optional query parameters

    Returns:
        The response object

    Raises:
        requests.HTTPError: If the request fails
    """
    jira_url = require_env("JIRA_URL")
    jira_user = require_env("JIRA_USER")
    jira_token = require_env("JIRA_TOKEN")

    url = f"{jira_url.rstrip('/')}{endpoint}"

    response = requests.request(
        method=method,
        url=url,
        auth=(jira_user, jira_token),
        headers={"Content-Type": "application/json"},
        json=json_data,
        params=params,
    )

    response.raise_for_status()
    return response


def api_call(
    endpoint: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Make a Jira API call and return the JSON response.

    Args:
        endpoint: API endpoint path
        method: HTTP method (default: GET)
        json_data: Optional JSON body
        params: Optional query parameters

    Returns:
        The JSON response as a dictionary

    Raises:
        requests.HTTPError: If the request fails
    """
    response = make_request(method, endpoint, json_data, params)
    return response.json()


def api_call_with_retry(
    endpoint: str,
    method: str = "GET",
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Dict[str, Any]:
    """
    Make a Jira API call with exponential backoff retry logic.

    Args:
        endpoint: API endpoint path
        method: HTTP method (default: GET)
        json_data: Optional JSON body
        params: Optional query parameters
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Initial delay between retries in seconds (default: 1.0)

    Returns:
        The JSON response as a dictionary

    Raises:
        requests.HTTPError: If all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return api_call(endpoint, method, json_data, params)
        except requests.HTTPError as e:
            last_exception = e
            # Don't retry on 4xx errors (client errors)
            if e.response.status_code < 500:
                raise

            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)
                print(f"Request failed (attempt {attempt + 1}/{max_retries}), retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)

    # All retries failed
    raise last_exception


def get_issue(issue_key: str, fields: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch a Jira issue by key.

    Args:
        issue_key: The Jira issue key (e.g., 'PROJ-123')
        fields: Optional comma-separated list of fields to return

    Returns:
        The issue data as a dictionary

    Raises:
        requests.HTTPError: If the request fails
    """
    params = {}
    if fields:
        params["fields"] = fields

    endpoint = f"/rest/api/2/issue/{issue_key}"
    return api_call_with_retry(endpoint, params=params)


def add_labels(issue_key: str, labels: list[str]) -> Dict[str, Any]:
    """
    Add labels to a Jira issue.

    This function fetches the current labels and merges them with the new labels
    to avoid removing existing labels.

    Args:
        issue_key: The Jira issue key (e.g., 'PROJ-123')
        labels: List of labels to add

    Returns:
        The updated issue data

    Raises:
        requests.HTTPError: If the request fails
    """
    # Fetch current issue to get existing labels
    issue = get_issue(issue_key, fields="labels")
    existing_labels = issue.get("fields", {}).get("labels", [])

    # Merge labels (remove duplicates)
    all_labels = list(set(existing_labels + labels))

    # Update the issue
    endpoint = f"/rest/api/2/issue/{issue_key}"
    update_data = {"fields": {"labels": all_labels}}

    return api_call_with_retry(endpoint, method="PUT", json_data=update_data)
