#!/usr/bin/env python3
"""
ui_cleanup.py — Delete cluster resources created during the test session.

Reads ui-cleanup-manifest.txt and removes any projects/DSPAs listed.
Compares the pre-test project snapshot to detect leftovers.

Usage:
    python3 ui_cleanup.py
"""
import json
import subprocess
import sys
from pathlib import Path

from paths import SKILL_DIR, TMP_DIR
manifest = TMP_DIR / "ui-cleanup-manifest.txt"
if manifest.exists():
    for line in manifest.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        rtype, name = line.split(": ", 1)
        if rtype == "project":
            if not name.startswith("qa-uiv-"):
                print(f"  ⚠️  Skipping project '{name}' — does not match qa-uiv-* prefix")
                continue
            subprocess.run(
                ["oc", "delete", "project", name, "--timeout=120s"],
                capture_output=True,
            )
        elif rtype == "dspa":
            n, ns = name.split("/")
            subprocess.run(
                ["oc", "delete", "datasciencepipelinesapplication", n,
                 "-n", ns, "--timeout=60s"],
                capture_output=True,
            )

ctx_path = TMP_DIR / "ui_context.json"
if ctx_path.exists():
    ctx = json.loads(ctx_path.read_text())
    if ctx.get("oc_available"):
        r = subprocess.run(
            ["oc", "get", "projects", "--no-headers",
             "-o", "custom-columns=NAME:.metadata.name"],
            capture_output=True, text=True,
        )
        extra = (set(r.stdout.strip().splitlines())
                 - set(ctx.get("pre_projects", []))
                 - {""})
        print("Leftover: " + str(extra) if extra else "Cluster restored")

for f in ["ui-cleanup-manifest.txt", "ui-existing-projects.txt"]:
    (TMP_DIR / f).unlink(missing_ok=True)

print("Cleanup done")
