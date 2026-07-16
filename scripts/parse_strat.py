#!/usr/bin/env python3
"""Parse sections from fetched STRAT content (Jira wiki markup).

Extracts acceptance criteria, non-functional requirements, and
out-of-scope items from the output of fetch_issue.py.

Usage:
    uv run python scripts/parse_strat.py acceptance-criteria <strat_file>
    uv run python scripts/parse_strat.py nfr <strat_file>
    uv run python scripts/parse_strat.py out-of-scope <strat_file>
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.utils.strat_utils import parse_acceptance_criteria, parse_nfr, parse_out_of_scope


def cmd_acceptance_criteria(args):
    content = Path(args.strat_file).read_text()
    result = parse_acceptance_criteria(content)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["found"] and result["count"] > 0 else 1)


def cmd_nfr(args):
    content = Path(args.strat_file).read_text()
    result = parse_nfr(content)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["found"] else 1)


def cmd_out_of_scope(args):
    content = Path(args.strat_file).read_text()
    result = parse_out_of_scope(content)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["found"] else 1)


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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
