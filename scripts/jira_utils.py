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
from typing import Any
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
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
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
        timeout=60,
    )

    response.raise_for_status()
    return response


def api_call(
    endpoint: str,
    method: str = "GET",
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Make a Jira API call and return the JSON response.

    Args:
        endpoint: API endpoint path
        method: HTTP method (default: GET)
        json_data: Optional JSON body
        params: Optional query parameters

    Returns:
        The JSON response as a dictionary, or None for empty responses (e.g., 204 No Content)

    Raises:
        requests.HTTPError: If the request fails
    """
    response = make_request(method, endpoint, json_data, params)

    # Handle empty responses (e.g., 204 No Content from PUT/DELETE)
    if response.status_code == 204 or not response.content:
        return None

    return response.json()


def api_call_with_retry(
    endpoint: str,
    method: str = "GET",
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> dict[str, Any] | None:
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

            # Don't retry auth errors (401, 403) - credentials won't fix themselves
            if e.response.status_code in (401, 403):
                print(
                    f"Authentication error ({e.response.status_code}): Check JIRA_URL, JIRA_USER, JIRA_TOKEN",
                    file=sys.stderr,
                )
                raise

            # Don't retry other 4xx errors (client errors like 404, 400)
            if e.response.status_code < 500:
                raise

            # Retry 5xx server errors (transient issues)
            if attempt < max_retries - 1:
                delay = retry_delay * (2**attempt)
                print(f"Request failed (attempt {attempt + 1}/{max_retries}), retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)

    # All retries failed
    raise last_exception


def get_issue(issue_key: str, fields: str | None = None) -> dict[str, Any]:
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


def add_labels(issue_key: str, labels: list[str]) -> None:
    """
    Add labels to a Jira issue.

    This function fetches the current labels and merges them with the new labels
    to avoid removing existing labels. Preserves label order and only makes API
    calls when labels actually change.

    Args:
        issue_key: The Jira issue key (e.g., 'PROJ-123')
        labels: List of labels to add

    Raises:
        requests.HTTPError: If the request fails
    """
    # Fetch current issue to get existing labels
    issue = get_issue(issue_key, fields="labels")
    existing_labels = issue.get("fields", {}).get("labels", [])

    # Merge labels preserving order (append new ones at end, deduplicate)
    all_labels = existing_labels.copy()
    for label in labels:
        if label not in all_labels:
            all_labels.append(label)

    # Only update if labels actually changed
    if all_labels == existing_labels:
        return

    # Update the issue (returns None for 204 No Content)
    endpoint = f"/rest/api/2/issue/{issue_key}"
    update_data = {"fields": {"labels": all_labels}}

    api_call_with_retry(endpoint, method="PUT", json_data=update_data)
