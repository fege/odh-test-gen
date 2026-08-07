#!/usr/bin/env python3
"""Parse sections from fetched STRAT content (Jira wiki markup).

Extracts acceptance criteria, non-functional requirements, and
out-of-scope items from the output of fetch_issue.py.

Usage:
    uv run python scripts/parse_strat.py acceptance-criteria <strat_file>
    uv run python scripts/parse_strat.py nfr <strat_file>
    uv run python scripts/parse_strat.py out-of-scope <strat_file>
    uv run python scripts/parse_strat.py workflow-inputs <strat_file>
    uv run python scripts/parse_strat.py resolve-local <jira_key>
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

from scripts.utils.repo_utils import get_git_root
from scripts.utils.schemas import SCHEMAS
from scripts.utils.strat_utils import parse_acceptance_criteria, parse_nfr, parse_out_of_scope, workflow_inputs

JIRA_KEY_RE = re.compile(SCHEMAS["test-plan"]["source_key"]["pattern"])


def _load_strat_content(raw_path: str) -> str:
    """Read strat_file after confirming it resolves inside a permitted location.

    Every documented caller passes one of exactly two paths: a `mktemp` temp file (Jira fetch)
    or `<repo_root>/artifacts/strat-tasks/<KEY>.md` (local cache fallback, keyed off a Jira issue
    key an upstream caller may not have validated). Anything else is rejected so a malformed or
    malicious strat_file argument can't be used to read arbitrary files off disk.
    """
    resolved = Path(raw_path).resolve()
    allowed_roots = [Path(tempfile.gettempdir()).resolve()]
    if repo_root := get_git_root(str(Path(__file__).resolve().parent)):
        allowed_roots.append((Path(repo_root) / "artifacts" / "strat-tasks").resolve())

    if not any(resolved == root or resolved.is_relative_to(root) for root in allowed_roots):
        raise ValueError("strategy_file_not_permitted")

    return resolved.read_text()


def cmd_acceptance_criteria(args):
    try:
        content = _load_strat_content(args.strat_file)
    except (ValueError, OSError):
        print(json.dumps({"status": "error", "error": "strategy_file_unreadable"}, indent=2))
        sys.exit(1)
    result = parse_acceptance_criteria(content)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["found"] and result["count"] > 0 else 1)


def cmd_nfr(args):
    try:
        content = _load_strat_content(args.strat_file)
    except (ValueError, OSError):
        print(json.dumps({"status": "error", "error": "strategy_file_unreadable"}, indent=2))
        sys.exit(1)
    result = parse_nfr(content)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["found"] else 1)


def cmd_out_of_scope(args):
    try:
        content = _load_strat_content(args.strat_file)
    except (ValueError, OSError):
        print(json.dumps({"status": "error", "error": "strategy_file_unreadable"}, indent=2))
        sys.exit(1)
    result = parse_out_of_scope(content)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["found"] else 1)


def cmd_resolve_local(args):
    if not JIRA_KEY_RE.match(args.jira_key):
        print(json.dumps({"found": False, "error": "malformed_jira_key"}, indent=2))
        sys.exit(1)

    repo_root = get_git_root(str(Path(__file__).resolve().parent))
    if not repo_root:
        print(json.dumps({"found": False, "error": "repo_root_not_found"}, indent=2))
        sys.exit(1)

    strat_dir = (Path(repo_root) / "artifacts" / "strat-tasks").resolve()
    candidate = (strat_dir / f"{args.jira_key}.md").resolve()

    if not candidate.is_file() or not (candidate == strat_dir or candidate.is_relative_to(strat_dir)):
        print(json.dumps({"found": False, "error": "strategy_file_not_found"}, indent=2))
        sys.exit(1)

    print(json.dumps({"found": True, "strategy_file": str(candidate)}, indent=2))
    sys.exit(0)


def cmd_workflow_inputs(args):
    try:
        content = _load_strat_content(args.strat_file)
    except (ValueError, OSError):
        print(json.dumps({"status": "error", "error": "strategy_file_unreadable"}, indent=2))
        sys.exit(1)

    result = workflow_inputs(content)
    print(json.dumps(result, indent=2))
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Parse sections from fetched STRAT content",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_ac = subparsers.add_parser("acceptance-criteria", help="Extract acceptance criteria")
    p_ac.add_argument("strat_file", help="Path to fetched STRAT markdown file")
    p_ac.set_defaults(func=cmd_acceptance_criteria)

    p_nfr = subparsers.add_parser("nfr", help="Extract non-functional requirements")
    p_nfr.add_argument("strat_file", help="Path to fetched STRAT markdown file")
    p_nfr.set_defaults(func=cmd_nfr)

    p_oos = subparsers.add_parser("out-of-scope", help="Extract out-of-scope items")
    p_oos.add_argument("strat_file", help="Path to fetched STRAT markdown file")
    p_oos.set_defaults(func=cmd_out_of_scope)

    p_workflow = subparsers.add_parser(
        "workflow-inputs",
        help="Combined ac/nfr/out-of-scope parse + gate inputs for test-plan-create Step 1.5",
    )
    p_workflow.add_argument("strat_file", help="Path to fetched STRAT markdown file")
    p_workflow.set_defaults(func=cmd_workflow_inputs)

    p_resolve = subparsers.add_parser(
        "resolve-local", help="Validate a Jira key and resolve it to a cached artifacts/strat-tasks/ file"
    )
    p_resolve.add_argument("jira_key", help="Jira key, e.g. RHAISTRAT-1746")
    p_resolve.set_defaults(func=cmd_resolve_local)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
