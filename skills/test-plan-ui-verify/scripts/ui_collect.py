#!/usr/bin/env python3
"""
ui_collect.py — Collect test results into the session directory and clean up .tmp/.

Copies ui_tc_log.json to the session directory, removes temp artefacts from
the session dir (keeping tc_log.json, report.md, and screenshots), then
removes all contents of .tmp/.

Prints SESSION_DIR=<path> for Claude to record for Phase 6 report writing.

Usage:
    python3 ui_collect.py
"""
import shutil
import sys
from pathlib import Path

from paths import SKILL_DIR, TMP_DIR
session   = TMP_DIR / ".ui-session"
tc_log    = TMP_DIR / "ui_tc_log.json"

if not session.exists():
    print("ERROR: .ui-session symlink not found", file=sys.stderr)
    sys.exit(1)


if tc_log.exists():
    shutil.copy(str(tc_log), str(session / "tc_log.json"))

ctx_file = TMP_DIR / "ui_context.json"
if ctx_file.exists():
    shutil.copy(str(ctx_file), str(session / "ui_context.json"))

for f in session.iterdir():
    if f.is_dir():
        shutil.rmtree(f)
    elif (f.name not in {"tc_log.json", "report.md", "report.html", "ui_context.json"}
          and "verify" not in f.name):
        f.unlink(missing_ok=True)

session_resolved = session.resolve()
print(f"SESSION_DIR={session_resolved}")
print("Files:", sorted(p.name for p in session.iterdir()))

# Clean up .tmp — results are now in results/<session>/
for item in list(TMP_DIR.iterdir()):
    try:
        if item.is_symlink() or item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    except Exception as e:
        print(f"  warning: could not remove {item.name}: {e}")

print(".tmp cleaned up")
