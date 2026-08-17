#!/usr/bin/env python3
"""Consolidate analyzer gaps, stamp TestPlanGaps.md frontmatter, and clean up staged output.

Wraps consolidate_gaps() + write_frontmatter_with_body() into the single call
test-plan-create's Step 3.5 needs, for both the initial run and the doc-resolution
re-run: the caller stages each analyzer's full raw output to a temp file, passes the
paths here, and this script consolidates, writes TestPlanGaps.md (body + frontmatter
in one shot), optionally deletes the temp files, and prints
{"gap_count": int, "status": str, "next": "proceed"|"prompt_user"}.

Usage:
    uv run python scripts/consolidate_gaps_and_stamp.py \
        --feature-name "<name>" --source-key RHAISTRAT-400 \
        --source endpoints=<path> --source risks=<path> --source infra=<path> \
        --last-updated YYYY-MM-DD \
        --out <feature_dir>/TestPlanGaps.md

Exits 1 (JSON to stdout) if a source file is missing/malformed or frontmatter write
fails. Temp source files are only deleted after TestPlanGaps.md is written successfully.
last_updated comes from --last-updated or, if omitted, from SOURCE_DATE_EPOCH (UTC date).
`next` is `prompt_user` only when gap_count > 0 and the session is interactive; otherwise
`proceed` (including CI / CLAUDE_NON_INTERACTIVE).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.utils.consolidate_gaps import consolidate_gaps, read_sources
from scripts.utils.error_utils import exit_error_with_json
from scripts.utils.frontmatter_utils import write_frontmatter_with_body
from scripts.utils.schemas import ValidationError
from scripts.validate import check_interactive


def _verified_staging_path(name: str, path: str, out_path: str) -> Path | None:
    """Return the staging file to delete if *path* is the expected analyzer temp file.

    Expected staging files are ``<feature_dir>/.analysis-{name}.md``, where *feature_dir*
    is the parent of *out_path*. Returns None (skip cleanup) when the source is not that
    file, including when it resolves to *out_path* itself — cleanup must not delete the
    newly written TestPlanGaps.md.
    """
    if Path(name).name != name or name in ("", ".", ".."):
        return None

    feature_dir = Path(out_path).resolve().parent
    expected = feature_dir / f".analysis-{name}.md"
    try:
        resolved = Path(path).resolve()
        resolved_out = Path(out_path).resolve()
        resolved_expected = expected.resolve()
    except OSError:
        return None

    # Never unlink TestPlanGaps.md, including when a staging path is a symlink to it.
    if resolved == resolved_out:
        return None
    if resolved != resolved_expected:
        return None
    return expected


def _resolve_last_updated(explicit: str | None) -> str:
    """Return an ISO date from *explicit* or SOURCE_DATE_EPOCH (UTC)."""
    if explicit:
        return explicit
    raw = os.environ.get("SOURCE_DATE_EPOCH")
    if not raw:
        raise ValueError("last_updated_required")
    try:
        return datetime.fromtimestamp(int(raw), timezone.utc).date().isoformat()
    except (OSError, OverflowError, ValueError) as e:
        raise ValueError("last_updated_required") from e


def decide_gaps_next(gap_count: int, *, interactive: bool) -> str:
    """Return the Step 3.5 action: prompt the user, or skip the gaps menu."""
    if gap_count > 0 and interactive:
        return "prompt_user"
    return "proceed"


def consolidate_and_stamp(
    feature_name: str,
    source_key: str,
    source_args: list[str],
    out_path: str,
    *,
    last_updated: str,
    cleanup: bool = True,
) -> dict:
    """Consolidate staged analyzer output, stamp TestPlanGaps.md, and optionally delete the staged files.

    Args:
        feature_name: feature name for the rendered body header and frontmatter.
        source_key: Jira source key stamped into frontmatter.
        source_args: repeatable "NAME=PATH" pairs, same shape as consolidate_gaps.py --source.
        out_path: path to write TestPlanGaps.md.
        last_updated: ISO date (YYYY-MM-DD) stamped into frontmatter.
        cleanup: if True (default), delete verified staging files after successful write.
            Set to False to preserve staged files for a potential re-run (e.g. doc-resolution path).

    Returns:
        {"gap_count": int, "status": "Open"|"Resolved"}

    Raises:
        ValueError: if a --source argument is malformed or unreadable. Staged files
        are left in place.
        ValidationError, OSError: if writing TestPlanGaps.md fails. Staged files are left
        in place in this case so the caller can retry or debug.
    """
    sources = read_sources(source_args)
    result = consolidate_gaps(sources, feature_name=feature_name)

    frontmatter = {
        "feature": feature_name,
        "source_key": source_key,
        "status": result["status"],
        "gap_count": result["gap_count"],
        "last_updated": last_updated,
    }
    write_frontmatter_with_body(out_path, result["body"], frontmatter, "test-gaps")

    if cleanup:
        # Best-effort: TestPlanGaps.md is already correct, so a stray permission error on
        # cleanup shouldn't fail an otherwise-successful run. Only delete verified staging
        # files inside the feature directory; skip anything else, including out_path.
        for entry in source_args:
            name, path = entry.split("=", 1)
            verified = _verified_staging_path(name, path, out_path)
            if verified is None:
                continue
            try:
                os.remove(verified)
            except OSError:
                pass

    return {"gap_count": result["gap_count"], "status": result["status"]}


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate analyzer gaps and stamp TestPlanGaps.md frontmatter",
    )
    parser.add_argument("--feature-name", required=True, help="Feature name for the rendered body header")
    parser.add_argument("--source-key", required=True, help="Jira source key, e.g. RHAISTRAT-400")
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        dest="sources",
        metavar="NAME=PATH",
        help="Analyzer name=path pair (repeatable), e.g. --source endpoints=<path>",
    )
    parser.add_argument("--out", required=True, help="Path to write TestPlanGaps.md")
    parser.add_argument(
        "--last-updated",
        default=None,
        help="ISO date (YYYY-MM-DD) for frontmatter last_updated. "
        "If omitted, derived from SOURCE_DATE_EPOCH (UTC date).",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Do not delete the staged .analysis-*.md files after writing TestPlanGaps.md. "
        "Use for re-runs (e.g. doc-resolution path) that need the staged files to persist.",
    )
    args = parser.parse_args()

    try:
        last_updated = _resolve_last_updated(args.last_updated)
        result = consolidate_and_stamp(
            args.feature_name,
            args.source_key,
            args.sources,
            args.out,
            last_updated=last_updated,
            cleanup=not args.skip_cleanup,
        )
        result["next"] = decide_gaps_next(
            result["gap_count"],
            interactive=check_interactive()["interactive"],
        )
    except ValueError as e:
        exit_error_with_json({"status": "failed", "error": str(e)})
    except (ValidationError, OSError) as e:
        exit_error_with_json({"status": "failed", "error": "write_failed"}, message=f"Error: {e}")

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
