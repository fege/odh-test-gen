"""Tests for PR operations — pr_create, pr_comments."""

import json
from unittest.mock import patch, MagicMock

from scripts.repo import pr_create, pr_comments


def test_creates_pr_when_none_exists():
    """Creates a new PR when no existing PR is found for the branch."""
    with patch("subprocess.run") as mock_run:

        def side_effect(cmd, **kwargs):
            if cmd[:3] == ["gh", "pr", "list"]:
                return MagicMock(returncode=0, stdout="[]\n")
            if cmd[:3] == ["gh", "pr", "create"]:
                return MagicMock(
                    returncode=0,
                    stdout="https://github.com/org/repo/pull/42\n",
                )
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        exit_code, result = pr_create(
            "org/repo",
            "test-plan/RHAISTRAT-400",
            "Test Plan: feature",
            "PR body",
        )

    assert exit_code == 0
    assert result["created"] is True
    assert result["pr_number"] == 42
    assert "github.com" in result["pr_url"]


def test_detects_existing_pr():
    """Returns existing PR info without creating a new one."""
    with patch("subprocess.run") as mock_run:

        def side_effect(cmd, **kwargs):
            if cmd[:3] == ["gh", "pr", "list"]:
                return MagicMock(
                    returncode=0,
                    stdout='[{"number": 7, "url": "https://github.com/org/repo/pull/7"}]\n',
                )
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        exit_code, result = pr_create(
            "org/repo",
            "test-plan/RHAISTRAT-400",
            "Title",
            "Body",
        )

    assert exit_code == 0
    assert result["created"] is False
    assert result["pr_number"] == 7
    create_calls = [c for c in mock_run.call_args_list if c[0][0][:3] == ["gh", "pr", "create"]]
    assert not create_calls


def test_creates_pr_with_reviewers():
    """Passes --reviewer flag when reviewers are provided."""
    with patch("subprocess.run") as mock_run:

        def side_effect(cmd, **kwargs):
            if cmd[:3] == ["gh", "pr", "list"]:
                return MagicMock(returncode=0, stdout="[]\n")
            if cmd[:3] == ["gh", "pr", "create"]:
                return MagicMock(
                    returncode=0,
                    stdout="https://github.com/org/repo/pull/1\n",
                )
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        pr_create("org/repo", "branch", "Title", "Body", reviewers="alice,bob")

    create_calls = [c for c in mock_run.call_args_list if c[0][0][:3] == ["gh", "pr", "create"]]
    create_cmd = create_calls[0][0][0]
    assert "--reviewer" in create_cmd
    assert "alice,bob" in create_cmd


def test_returns_error_when_pr_url_unparseable():
    """Returns error when gh pr create output doesn't contain a PR number."""
    with patch("subprocess.run") as mock_run:

        def side_effect(cmd, **kwargs):
            if cmd[:3] == ["gh", "pr", "list"]:
                return MagicMock(returncode=0, stdout="[]\n")
            if cmd[:3] == ["gh", "pr", "create"]:
                return MagicMock(
                    returncode=0,
                    stdout="some-unexpected-output\n",
                )
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        exit_code, result = pr_create(
            "org/repo",
            "branch",
            "Title",
            "Body",
        )

    assert exit_code == 1
    assert "error" in result


def test_creates_pr_without_reviewers():
    """Does not pass --reviewer flag when no reviewers provided."""
    with patch("subprocess.run") as mock_run:

        def side_effect(cmd, **kwargs):
            if cmd[:3] == ["gh", "pr", "list"]:
                return MagicMock(returncode=0, stdout="[]\n")
            if cmd[:3] == ["gh", "pr", "create"]:
                return MagicMock(
                    returncode=0,
                    stdout="https://github.com/org/repo/pull/1\n",
                )
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        pr_create("org/repo", "branch", "Title", "Body")

    create_calls = [c for c in mock_run.call_args_list if c[0][0][:3] == ["gh", "pr", "create"]]
    create_cmd = create_calls[0][0][0]
    assert "--reviewer" not in create_cmd


def _ndjson(items):
    """Convert a list of dicts to NDJSON (one JSON object per line)."""
    return "\n".join(json.dumps(item) for item in items)


def test_pr_comments_merges_conversation_and_inline():
    """Merges conversation comments, reviews, and inline comments."""
    conv_json = _ndjson(
        [
            {"user": {"login": "alice"}, "body": "Looks good overall"},
        ]
    )
    review_json = _ndjson(
        [
            {"user": {"login": "bob"}, "body": "Some concerns", "state": "CHANGES_REQUESTED"},
        ]
    )
    inline_json = _ndjson(
        [
            {"user": {"login": "bob"}, "body": "Fix this line", "path": "TestPlan.md", "line": 42},
        ]
    )

    with patch("subprocess.run") as mock_run:

        def side_effect(cmd, **kwargs):
            endpoint = cmd[-1]
            if endpoint.endswith("/issues/42/comments"):
                return MagicMock(returncode=0, stdout=conv_json)
            if endpoint.endswith("/pulls/42/reviews"):
                return MagicMock(returncode=0, stdout=review_json)
            if endpoint.endswith("/pulls/42/comments"):
                return MagicMock(returncode=0, stdout=inline_json)
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        exit_code, comments = pr_comments("org/repo", 42)

    assert exit_code == 0
    assert len(comments) == 3
    types = {c["type"] for c in comments}
    assert types == {"conversation", "review", "inline"}
    authors = {c["author"] for c in comments}
    assert authors == {"alice", "bob"}


def test_pr_comments_filters_bot_comments():
    """Filters out comments from bot accounts with [bot] suffix."""
    conv_json = _ndjson(
        [
            {"user": {"login": "alice"}, "body": "Real comment"},
            {"user": {"login": "coderabbitai[bot]"}, "body": "Auto summary"},
        ]
    )
    review_json = ""
    inline_json = _ndjson(
        [
            {"user": {"login": "github-actions[bot]"}, "body": "CI passed", "path": "f.md", "line": 1},
        ]
    )

    with patch("subprocess.run") as mock_run:

        def side_effect(cmd, **kwargs):
            endpoint = cmd[-1]
            if endpoint.endswith("/issues/42/comments"):
                return MagicMock(returncode=0, stdout=conv_json)
            if endpoint.endswith("/pulls/42/reviews"):
                return MagicMock(returncode=0, stdout=review_json)
            if endpoint.endswith("/pulls/42/comments"):
                return MagicMock(returncode=0, stdout=inline_json)
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        exit_code, comments = pr_comments("org/repo", 42)

    assert exit_code == 0
    assert len(comments) == 1
    assert comments[0]["author"] == "alice"


def test_pr_comments_uses_paginate_with_jq():
    """All gh api calls include --paginate and --jq for safe pagination."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        pr_comments("org/repo", 42)

    api_calls = [c[0][0] for c in mock_run.call_args_list if "api" in c[0][0]]
    assert len(api_calls) == 3
    for cmd in api_calls:
        assert "--paginate" in cmd, f"Missing --paginate in {cmd}"
        assert "--jq" in cmd, f"Missing --jq in {cmd}"


def test_pr_comments_empty_when_no_comments():
    """Returns empty list when PR has no comments."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        exit_code, comments = pr_comments("org/repo", 42)

    assert exit_code == 0
    assert comments == []


def test_pr_comments_handles_multipage_ndjson():
    """Handles multi-page NDJSON output from gh api --paginate --jq '.[]'."""
    comment1 = {"user": {"login": "alice"}, "body": "Comment 1"}
    comment2 = {"user": {"login": "bob"}, "body": "Comment 2"}
    multipage_conv = json.dumps(comment1) + "\n" + json.dumps(comment2)

    with patch("subprocess.run") as mock_run:

        def side_effect(cmd, **kwargs):
            endpoint = cmd[-1]
            if endpoint.endswith("/issues/42/comments"):
                return MagicMock(returncode=0, stdout=multipage_conv)
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = side_effect

        exit_code, comments = pr_comments("org/repo", 42)

    assert exit_code == 0
    assert len(comments) == 2
    assert comments[0]["body"] == "Comment 1"
    assert comments[1]["body"] == "Comment 2"
