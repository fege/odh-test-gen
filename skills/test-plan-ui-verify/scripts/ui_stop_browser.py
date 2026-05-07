#!/usr/bin/env python3
"""
ui_stop_browser.py — Stop the persistent browser launched by ui_prepare.py.

Reads the browser PID from ui_context.json and sends SIGTERM.

Usage:
    python3 ui_stop_browser.py
"""
import json
import os
import signal
import sys
from pathlib import Path

from paths import SKILL_DIR, TMP_DIR
ctx_path  = SKILL_DIR / ".tmp" / "ui_context.json"

if not ctx_path.exists():
    print("No context found — browser already stopped or never started.")
    sys.exit(0)

ctx = json.loads(ctx_path.read_text())
pid = ctx.get("browser_pid")

if pid:
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Browser (pid={pid}) stopped")
    except ProcessLookupError:
        print(f"Browser (pid={pid}) already stopped")
else:
    print("No browser PID in context")
