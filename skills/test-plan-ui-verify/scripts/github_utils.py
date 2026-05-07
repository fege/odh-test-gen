#!/usr/bin/env python3
"""GitHub API helpers for test-plan.ui-verify.

Functions for fetching TC files and metadata from GitHub via the gh CLI.
"""
import base64
import json
import re
import subprocess

import yaml

from helpers import matches_tc_filter as _matches_tc_filter


def _run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def fetch_file(repo: str, path: str, ref: str) -> str | None:
    """Fetch a single file's decoded content from the GitHub Contents API."""
    r = _run(["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}", "--jq", ".content"])
    if r.returncode != 0:
        return None
    raw = r.stdout.strip().strip('"').replace("\\n", "\n")
    try:
        return base64.b64decode(raw).decode()
    except Exception:
        return raw


def fetch_meta(repo: str, feature: str, ref: str) -> dict:
    """Read TestPlan.md frontmatter for feature/strat_key."""
    content = fetch_file(repo, f"{feature}/TestPlan.md", ref)
    if not content or not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm = yaml.safe_load(content[3:end]) or {}
    return {"feature": fm.get("feature", feature), "strat_key": fm.get("strat_key", "")}


def fetch_tc_files(repo: str, feature: str, ref: str,
                   tc_patterns: list) -> list[tuple[str, str]]:
    """Fetch matching TC-*.md files. Returns [(filename, content)].

    Raises RuntimeError if the GitHub API call fails.
    """
    exact_id = re.compile(r'^TC-[A-Z0-9]+-\d+$')

    def matches(tc_id: str) -> bool:
        return _matches_tc_filter(tc_id, tc_patterns)

    # Fast path: all patterns are exact IDs — fetch directly without listing
    if tc_patterns and all(exact_id.match(p) for p in tc_patterns):
        filenames = [f"{p}.md" for p in tc_patterns]
        print(f"  Fetching {len(filenames)} TC file(s) directly...", flush=True)
        out = []
        for i, name in enumerate(filenames, 1):
            print(f"  [{i}/{len(filenames)}] {name}", flush=True)
            content = fetch_file(repo, f"{feature}/test_cases/{name}", ref)
            if content:
                out.append((name, content))
            else:
                print(f"  ⚠️  {name} not found", flush=True)
        return out

    # General path: list then filter then fetch
    print(f"  Fetching file list from {repo}/{feature}...", flush=True)
    r = _run(["gh", "api", f"repos/{repo}/contents/{feature}/test_cases?ref={ref}",
              "--jq", '[.[] | select(.name | test("TC-.*[.]md")) | .name]'])
    if r.returncode != 0:
        raise RuntimeError(f"Failed to fetch TC file list: {r.stderr.strip()}")
    all_names = json.loads(r.stdout)
    if tc_patterns:
        all_names = [n for n in all_names if matches(n.replace(".md", ""))]
    print(f"  Found {len(all_names)} matching TC file(s) — fetching...", flush=True)
    out = []
    for i, name in enumerate(sorted(all_names), 1):
        print(f"  [{i}/{len(all_names)}] {name}", flush=True)
        content = fetch_file(repo, f"{feature}/test_cases/{name}", ref)
        if content:
            out.append((name, content))
    return out
