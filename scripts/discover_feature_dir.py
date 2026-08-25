#!/usr/bin/env python3
"""Read the saved output-dir marker from a feature directory.

`/test-plan-create` always writes `<feature_dir>/.test-plan-output-dir.json` (via
`parse_strat.py save-snapshot`), making the feature directory self-contained: it carries its
own metadata instead of relying on a separate settings file to rediscover it. This script's only
job is to read and validate that marker file for a given feature directory.

Usage:
    uv run python scripts/discover_feature_dir.py <feature_dir>
    echo <feature_dir> | uv run python scripts/discover_feature_dir.py
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.parse_strat import OUTPUT_DIR_MARKER
from scripts.utils.error_utils import exit_error_with_json


def discover_feature_dir(feature_dir: str) -> dict:
    """Read and parse `<feature_dir>/.test-plan-output-dir.json`.

    Returns the marker file's contents as-is (e.g. ``{"output_dir": "...", ...}``), whatever
    keys it happens to carry — this script does not police the schema beyond "valid JSON
    object", so the marker can grow new fields later without coordination here.

    Raises:
        ValueError: If the marker file is missing, unreadable, not valid JSON, or not a JSON object.
    """
    marker_path = Path(feature_dir) / OUTPUT_DIR_MARKER

    if not marker_path.is_file():
        raise ValueError(f"{OUTPUT_DIR_MARKER} not found in {feature_dir}")

    try:
        content = marker_path.read_text()
    except OSError as e:
        raise ValueError(f"Could not read {marker_path}: {e}") from e

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {marker_path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"Invalid marker object in {marker_path}")

    return data


def main():
    parser = argparse.ArgumentParser(
        description="Read the saved output-dir marker from a feature directory (RHAIFIRST-580)"
    )
    parser.add_argument(
        "feature_dir",
        nargs="?",
        default=None,
        help="Path to the feature directory (reads from stdin if omitted)",
    )
    args = parser.parse_args()

    feature_dir = args.feature_dir
    if feature_dir is None:
        feature_dir = sys.stdin.read().strip()

    if not feature_dir:
        exit_error_with_json(message="No feature directory provided", error_key="missing_feature_dir")

    try:
        result = discover_feature_dir(feature_dir)
        print(json.dumps(result, indent=2))
    except ValueError as e:
        exit_error_with_json(message=str(e), error_key="invalid_output_dir_marker")


if __name__ == "__main__":
    main()
