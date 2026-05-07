#!/usr/bin/env python3
"""
build_element_map.py — Scans the ODH Dashboard source for data-testid attributes
and generates element-map.yaml for fast element location during TC execution.

Usage:
    python3 build_element_map.py --source /path/to/odh-dashboard
    python3 build_element_map.py --source /path/to/odh-dashboard --out element-map.yaml

Run this whenever the dashboard source changes significantly.
The output is committed to the skill repo and used at runtime — no snapshot needed.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path
from collections import defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(1)

# Map file paths to logical section names
SECTION_PATTERNS = [
    (r"model.catalog|modelCatalog|ai.hub|aiHub",                   "catalog"),
    (r"pipeline|Pipeline",                                          "pipelines"),
    (r"model.serving|modelServing|inference|InferenceService",      "model-serving"),
    (r"model.registry|modelRegistry",                               "model-registry"),
    (r"notebook|Notebook|spawner|Spawner|workbench|Workbench",      "workbenches"),
    (r"project|Project",                                            "projects"),
    (r"connection|Connection",                                      "connections"),
    (r"cluster.setting|ClusterSetting|settings|Settings",          "cluster-settings"),
    (r"distributed.workload|DistributedWorkload",                   "distributed-workloads"),
    (r"gen.ai|GenAI|chat|Chat|playground|Playground",               "gen-ai"),
    (r"model.training|ModelTraining",                               "model-training"),
]

# Patterns to skip (too generic or internal)
SKIP_PATTERNS = re.compile(
    r'^(app-|test-|mock-|story-|example-|placeholder|loading|spinner|skeleton)',
    re.IGNORECASE
)


def classify_file(filepath: str) -> str:
    for pattern, section in SECTION_PATTERNS:
        if re.search(pattern, filepath, re.IGNORECASE):
            return section
    return "general"


def extract_testids(source_dir: Path) -> dict:
    """Grep the source for data-testid attributes and return classified results."""
    result = subprocess.run(
        ["grep", "-r", "--include=*.tsx", "--include=*.ts",
         "-n", "data-testid", str(source_dir)],
        capture_output=True, text=True
    )

    sections = defaultdict(dict)
    seen_ids = set()

    # Match both: data-testid="value" and data-testid={'value'} and data-testid={`value`}
    testid_re = re.compile(r'data-testid[=:{]+["\'{`]([^"\'{}`\s]+)["\'{`]')

    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        filepath, rest = line.split(":", 1)

        # Skip test files and story files
        if any(x in filepath for x in [".spec.", ".test.", ".stories.", "__tests__", "__mocks__"]):
            continue

        for match in testid_re.finditer(rest):
            testid = match.group(1)

            # Skip too-generic or already-seen IDs
            if SKIP_PATTERNS.match(testid) or testid in seen_ids:
                continue

            seen_ids.add(testid)
            section = classify_file(filepath)

            # Convert kebab-case testid to a readable key
            key = testid.replace("-", " ").lower()
            sections[section][key] = f'[data-testid="{testid}"]'

    return dict(sections)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True,
                        help="Path to odh-dashboard repo root (e.g. /path/to/odh-dashboard)")
    parser.add_argument("--out", default=None,
                        help="Output file path (default: element-map.yaml next to this script)")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"ERROR: Source directory not found: {source}")
        sys.exit(1)

    frontend = source / "frontend" / "src"
    packages = source / "packages"
    scan_dirs = []
    if frontend.exists():
        scan_dirs.append(frontend)
    for p in packages.glob("*/frontend/src"):
        scan_dirs.append(p)

    if not scan_dirs:
        print(f"ERROR: No frontend/src directories found under {source}")
        sys.exit(1)

    print(f"Scanning {len(scan_dirs)} source directories...")
    all_sections = defaultdict(dict)
    for d in scan_dirs:
        result = extract_testids(d)
        for section, items in result.items():
            all_sections[section].update(items)

    total = sum(len(v) for v in all_sections.values())
    print(f"Found {total} unique data-testid attributes across {len(all_sections)} sections")

    out_path = Path(args.out) if args.out else Path(__file__).parent.parent / "element-map.yaml"

    # Sort sections and keys for stable output
    sorted_map = {
        section: dict(sorted(items.items()))
        for section, items in sorted(all_sections.items())
    }

    # Stamp with dashboard git commit for staleness tracking
    commit_r = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True
    )
    commit = commit_r.stdout.strip() if commit_r.returncode == 0 else "unknown"
    from datetime import datetime
    generated_at = datetime.now().strftime("%Y-%m-%d")

    header = (
        "# element-map.yaml — auto-generated from ODH Dashboard source\n"
        "# Maps semantic names to CSS selectors for fast element location.\n"
        "# Generated from: <odh-dashboard-checkout>\n"
        f"# Dashboard commit: {commit}  |  Generated: {generated_at}\n"
        "# Regenerate: python3 scripts/build_element_map.py --source /path/to/odh-dashboard\n"
        "#   or: python3 scripts/ui_prepare.py --refresh-map /path/to/odh-dashboard\n"
        "#\n"
        "# Stale entries don't break the skill — they fall back to text matching then snapshot.\n\n"
    )

    with open(out_path, "w") as f:
        f.write(header)
        yaml.dump(sorted_map, f, default_flow_style=False, allow_unicode=True)

    print(f"Written: {out_path}")
    for section, items in sorted(sorted_map.items()):
        print(f"  {section}: {len(items)} elements")


if __name__ == "__main__":
    main()
