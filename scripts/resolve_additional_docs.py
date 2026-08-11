#!/usr/bin/env python3
"""Resolve additional_docs from TestPlan.md frontmatter deterministically.

Reads the ``additional_docs`` list from ``<feature_dir>/TestPlan.md`` frontmatter,
classifies each entry (URL vs local path), applies symlink-safe containment for
local paths (must resolve inside ``<feature_dir>`` with no symlinks), and outputs
a JSON document with pre-validated content ready for prompt injection.

The LLM never touches path resolution — this script is the sole trust boundary.

Usage:
    uv run python scripts/resolve_additional_docs.py <feature_dir>

Exit 0 with ``{"status": "ok", "docs": [...]}`` on success (including when
``additional_docs`` is empty or absent).  Exit 1 with
``{"status": "error", "error": "<code>"}`` when TestPlan.md is missing/unreadable
or frontmatter is invalid.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

from scripts.utils.frontmatter_utils import read_frontmatter
from scripts.utils.snapshot_io import read_file_nofollow, require_within_feature_dir


def _is_url(entry: str) -> bool:
    """Return True if *entry* is an http(s) URL."""
    try:
        parsed = urlparse(entry)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _resolve_entry(entry: str, feature_dir: str) -> dict:
    """Classify and resolve a single ``additional_docs`` entry."""
    if _is_url(entry):
        return {"ref": entry, "kind": "url"}

    # --- Local path containment ---

    # Reject absolute paths before any resolution.
    if os.path.isabs(entry):
        return {"ref": entry, "kind": "local", "status": "skipped", "reason": "absolute_path"}

    # Reject explicit traversal components.
    parts = Path(entry).parts
    if ".." in parts:
        return {"ref": entry, "kind": "local", "status": "skipped", "reason": "traversal"}

    candidate = Path(feature_dir) / entry

    # Containment + symlink check (resolve, is_relative_to, is_symlink).
    try:
        safe_path = require_within_feature_dir(feature_dir, candidate)
    except ValueError as exc:
        # require_within_feature_dir raises with a stable reason code.
        return {"ref": entry, "kind": "local", "status": "skipped", "reason": str(exc)}

    # Symlink-safe read (O_NOFOLLOW).
    try:
        content = read_file_nofollow(safe_path)
    except OSError:
        return {"ref": entry, "kind": "local", "status": "skipped", "reason": "unreadable"}

    return {"ref": entry, "kind": "local", "status": "read", "content": content}


def resolve_additional_docs(feature_dir: str) -> dict:
    """Resolve all ``additional_docs`` entries from TestPlan.md frontmatter.

    Returns a dict suitable for JSON serialization:
    ``{"status": "ok", "docs": [...]}``.

    Raises on unreadable/missing TestPlan.md or invalid frontmatter (caller
    decides how to surface the error).
    """
    testplan_path = Path(feature_dir) / "TestPlan.md"

    # read_frontmatter returns ({}, body) when no frontmatter is found, and
    # raises FileNotFoundError when the file doesn't exist.
    try:
        data, _ = read_frontmatter(str(testplan_path))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise ValueError("invalid_frontmatter") from exc

    if not data:
        raise ValueError("no_frontmatter")

    additional_docs = data.get("additional_docs", [])
    if additional_docs is None:
        additional_docs = []
    if not isinstance(additional_docs, list) or not all(isinstance(entry, str) for entry in additional_docs):
        raise ValueError("invalid_additional_docs")

    docs = [_resolve_entry(str(entry), feature_dir) for entry in additional_docs]

    return {"status": "ok", "docs": docs}


def main():
    parser = argparse.ArgumentParser(
        description="Resolve additional_docs from TestPlan.md frontmatter",
    )
    parser.add_argument("feature_dir", help="Path to the feature directory containing TestPlan.md")
    args = parser.parse_args()

    try:
        result = resolve_additional_docs(args.feature_dir)
    except FileNotFoundError:
        print(json.dumps({"status": "error", "error": "testplan_not_found"}))
        sys.exit(1)
    except ValueError as exc:
        # Every ValueError raised by resolve_additional_docs is a stable, path-free code.
        print(json.dumps({"status": "error", "error": str(exc)}))
        sys.exit(1)
    except Exception:
        print(json.dumps({"status": "error", "error": "unexpected_failure"}))
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
