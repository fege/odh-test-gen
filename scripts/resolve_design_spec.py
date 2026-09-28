#!/usr/bin/env python3
"""Discover and snapshot a design-spec companion document for a STRAT.

Design specs may arrive as:
- An explicit local file path (highest precedence)
- A Jira attachment on the STRAT issue

Attachment selection (newest wins, same ordering as strategy attachments):
1. Exact ``{issue_key}-design-spec.md``
2. Fallback: any filename containing ``design-spec`` (case-insensitive), ending in ``.md``

Usage:
    uv run python scripts/resolve_design_spec.py --issue-key RHAISTRAT-400
    uv run python scripts/resolve_design_spec.py --issue-key RHAISTRAT-400 \\
        --local-path ./design-spec.md --feature-dir /path/to/feature --snapshot

Exit 0 with JSON on success (including ``source: none``). Exit 1 with
``{"status": "error", "error": "<code>"}`` on failure.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from scripts.jira_utils import AttachmentFetchError, download_attachment, get_issue
from scripts.strategy_source import _attachment_sort_key
from scripts.utils.error_utils import exit_error_with_json
from scripts.utils.snapshot_io import write_snapshot_nofollow

DESIGN_SPEC_SNAPSHOT = ".source-design-spec.md"
_DESIGN_SPEC_HEADING_RE = re.compile(r"^#\s+Design Spec\b", re.IGNORECASE | re.MULTILINE)
_DESIGN_SPEC_FILENAME_RE = re.compile(r"design[-_]?spec", re.IGNORECASE)

AttachmentDownloader = Callable[[str], str]


def looks_like_design_spec(path: str | Path, content: str | None = None) -> bool:
    """Return True when *path* or *content* indicates a design-spec document."""
    name = Path(path).name
    if _DESIGN_SPEC_FILENAME_RE.search(name):
        return True
    if content and _DESIGN_SPEC_HEADING_RE.search(content):
        return True
    return False


def classify_companion_doc(path: str | Path, content: str | None = None) -> str:
    """Classify a companion doc path as ``design_spec``, ``adr``, or ``other``."""
    name = Path(path).name.lower()
    if looks_like_design_spec(path, content):
        return "design_spec"
    if "adr" in name or name.startswith("architecture"):
        return "adr"
    if content and re.search(r"^#\s+Architecture Decision Record\b", content, re.IGNORECASE | re.MULTILINE):
        return "adr"
    return "other"


def select_design_spec_attachment(issue_key: str, attachments: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Select the newest design-spec attachment from a Jira attachment list.

    Prefers an exact ``{issue_key}-design-spec.md`` match. Falls back to any
    markdown filename containing ``design-spec`` (case-insensitive).
    """
    exact_name = f"{issue_key}-design-spec.md"
    exact = [a for a in attachments if a.get("filename") == exact_name]
    if exact:
        return max(exact, key=_attachment_sort_key)

    fallback = [
        a
        for a in attachments
        if isinstance(a.get("filename"), str)
        and a["filename"].lower().endswith(".md")
        and _DESIGN_SPEC_FILENAME_RE.search(a["filename"])
    ]
    return max(fallback, key=_attachment_sort_key, default=None)


def snapshot_design_spec(feature_dir: str, content: str) -> str:
    """Write design-spec content to ``<feature_dir>/.source-design-spec.md``.

    Returns the absolute path of the snapshot file.
    """
    feature_path = Path(feature_dir)
    feature_path.mkdir(parents=True, exist_ok=True)
    snapshot_path = feature_path / DESIGN_SPEC_SNAPSHOT
    write_snapshot_nofollow(snapshot_path, content)
    return str(snapshot_path)


def resolve_design_spec(
    *,
    issue_key: str | None = None,
    local_path: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    attachment_downloader: AttachmentDownloader | None = None,
    fetch_issue: bool = True,
) -> dict[str, Any]:
    """Resolve a design-spec from a local path or Jira attachments.

    Local path always wins when provided. Otherwise selects from *attachments*
    (or fetches the issue when *fetch_issue* is True and *issue_key* is set).

    Returns a dict suitable for JSON serialization.
    """
    if local_path:
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError("local_path_not_found")
        try:
            # Explicit user-provided paths may be symlinks; containment is enforced
            # when the content is later snapshotted into feature_dir.
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OSError("local_path_unreadable") from exc

        return {
            "status": "ok",
            "source": "local",
            "path": str(path.resolve()),
            "filename": path.name,
            "content": content,
            "kind": classify_companion_doc(path, content),
        }

    attachment_list = attachments
    if attachment_list is None and fetch_issue and issue_key:
        issue_data = get_issue(issue_key, fields="attachment")
        attachment_list = issue_data.get("fields", {}).get("attachment") or []

    if not issue_key or attachment_list is None:
        return {"status": "ok", "source": "none", "content": None}

    attachment = select_design_spec_attachment(issue_key, attachment_list)
    if not attachment or not attachment.get("content"):
        return {"status": "ok", "source": "none", "content": None}

    downloader = attachment_downloader if attachment_downloader is not None else download_attachment
    content = downloader(attachment["content"])
    filename = str(attachment.get("filename") or f"{issue_key}-design-spec.md")

    return {
        "status": "ok",
        "source": "attachment",
        "filename": filename,
        "content": content,
        "kind": "design_spec",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover and optionally snapshot a design-spec document")
    parser.add_argument("--issue-key", help="Jira issue key (e.g., RHAISTRAT-400)")
    parser.add_argument("--local-path", help="Local design-spec markdown path (wins over attachment)")
    parser.add_argument("--feature-dir", help="Feature directory for --snapshot")
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Write resolved content to <feature_dir>/.source-design-spec.md",
    )
    parser.add_argument(
        "--attachments-json",
        help="Optional JSON file with an attachment list (skips live Jira fetch; for tests)",
    )
    args = parser.parse_args()

    if not args.local_path and not args.issue_key:
        exit_error_with_json({"status": "error", "error": "missing_issue_or_local_path"})

    if args.snapshot and not args.feature_dir:
        exit_error_with_json({"status": "error", "error": "feature_dir_required_for_snapshot"})

    attachments = None
    fetch_issue = True
    if args.attachments_json:
        fetch_issue = False
        try:
            with open(args.attachments_json, encoding="utf-8") as f:
                payload = json.load(f)
            attachments = payload if isinstance(payload, list) else payload.get("attachment") or []
        except (OSError, json.JSONDecodeError):
            exit_error_with_json({"status": "error", "error": "attachments_json_unreadable"})

    try:
        result = resolve_design_spec(
            issue_key=args.issue_key,
            local_path=args.local_path,
            attachments=attachments,
            fetch_issue=fetch_issue,
        )
    except FileNotFoundError:
        exit_error_with_json({"status": "error", "error": "local_path_not_found"})
    except OSError:
        exit_error_with_json({"status": "error", "error": "local_path_unreadable"})
    except AttachmentFetchError:
        exit_error_with_json({"status": "error", "error": "attachment_fetch_failed"})
    except Exception:
        exit_error_with_json({"status": "error", "error": "unexpected_failure"})

    if args.snapshot and result.get("content"):
        try:
            snapshot_path = snapshot_design_spec(args.feature_dir, result["content"])
        except OSError:
            exit_error_with_json({"status": "error", "error": "snapshot_write_failed"})
        result["snapshot_path"] = snapshot_path
        result["additional_docs_entry"] = DESIGN_SPEC_SNAPSHOT

    # Omit large content from default CLI output unless --include-content is needed;
    # skills that need content use --snapshot and then Read the snapshot file.
    output = {k: v for k, v in result.items() if k != "content"}
    output["has_content"] = bool(result.get("content"))
    print(json.dumps(output, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
