#!/usr/bin/env python3
"""
ui_block.py — Log a BLOCKED step to the TC log.

Use when a TC step cannot be executed (element not found, prerequisite not met,
feature not deployed). Never substitute — always block with an exact reason.

Usage:
    python3 ui_block.py --tc <TC_ID> --reason "<specific reason>"
"""
import argparse
import json
import sys
from pathlib import Path

from paths import SKILL_DIR, TMP_DIR
TC_LOG    = SKILL_DIR / ".tmp" / "ui_tc_log.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tc",         required=True, help="TC ID e.g. TC-E2E-003")
    parser.add_argument("--title",      default="",   help="Human-readable TC title (stored in log for report)")
    parser.add_argument("--reason",     required=True, help="Specific reason this step is blocked")
    parser.add_argument("--what",       default="",   help="Optional: what was being attempted")
    parser.add_argument("--incomplete", action="store_true",
                        help="Mark TC as INCOMPLETE — execution was interrupted before finishing")
    args = parser.parse_args()

    log = {}
    if TC_LOG.exists():
        try:
            log = json.loads(TC_LOG.read_text())
        except Exception:
            pass

    if args.tc not in log:
        log[args.tc] = {"title": args.tc, "verdict": "BLOCKED", "assertions": [], "blocked_reason": ""}

    if args.title and log[args.tc].get("title") == args.tc:
        log[args.tc]["title"] = args.title

    # Verdict priority: FAIL > INCOMPLETE > BLOCKED > PASS
    current = log[args.tc]["verdict"]
    if args.incomplete:
        if current not in ("FAIL",):
            log[args.tc]["verdict"] = "INCOMPLETE"
    elif current not in ("FAIL", "INCOMPLETE"):
        log[args.tc]["verdict"] = "BLOCKED"
    log[args.tc]["blocked_reason"] = args.reason

    if args.what:
        log[args.tc]["assertions"].append({
            "checked":  args.what,
            "expected": "Step executable",
            "result":   "BLOCKED",
            "detail":   args.reason,
        })

    TC_LOG.parent.mkdir(parents=True, exist_ok=True)
    TC_LOG.write_text(json.dumps(log, indent=2))
    verdict = log[args.tc]["verdict"]
    icon = "🔴" if verdict == "INCOMPLETE" else "⚠️"
    print(f"{icon} {verdict} [{args.tc}]: {args.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
