#!/usr/bin/env python3
"""
ui_read_ctx.py — Print session context values and initialise the TC log.

Reads ui_context.json and prints each key=value on a line for Claude to
record as literals. Also creates ui_tc_log.json if it does not exist.

Usage:
    python3 ui_read_ctx.py
"""
import json
import sys
from pathlib import Path
from paths import SKILL_DIR, TMP_DIR

ctx_path = TMP_DIR / "ui_context.json"
if not ctx_path.exists():
    print("ERROR: context not found. Run ui_prepare.py first.")
    sys.exit(1)

ctx = json.loads(ctx_path.read_text())

for k in ["target_url", "cluster_api", "username", "idp",
          "skill_dir", "session_dir", "component", "feature",
          "browser_cdp", "browser_pid"]:
    print(f"{k.upper()}={ctx.get(k, '')}")

print(f"TC_COUNT={len(ctx['test_cases'])}")
print("KNOWN_ROUTES=" + json.dumps(ctx.get("known_routes", {})))

# Initialise TC log
tc_log = TMP_DIR / "ui_tc_log.json"
if not tc_log.exists():
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tc_log.write_text("{}")
