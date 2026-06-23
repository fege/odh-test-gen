#!/usr/bin/env python3
"""CLI for test plan version management.

Skills call this script instead of manually parsing and incrementing
version strings, ensuring consistent semver handling.

Usage:
    # Bump patch version: 1.0.0 → 1.0.1
    uv run python scripts/version.py bump <file> patch
    # Outputs JSON: {"old_version": "1.0.0", "new_version": "1.0.1"}

    # Bump minor version: 1.0.0 → 1.1.0
    uv run python scripts/version.py bump <file> minor

    # Bump major version: 1.0.0 → 2.0.0
    uv run python scripts/version.py bump <file> major

    # Set version to a specific value
    uv run python scripts/version.py set <file> 2.0.0
    # Outputs JSON: {"old_version": "1.0.0", "new_version": "2.0.0"}

Examples:
    uv run python scripts/version.py bump mcp_catalog/TestPlan.md patch
    uv run python scripts/version.py set mcp_catalog/TestPlan.md 2.0.0
"""

import argparse
import json
import os
import re
import sys
from datetime import date

from scripts.utils.frontmatter_utils import read_frontmatter, update_frontmatter
from scripts.utils.schemas import SCHEMAS, ValidationError, detect_schema_type

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def bump_version(version_str: str, bump_type: str) -> str:
    """Parse a semver string and increment the specified part.

    Args:
        version_str: Current version (e.g. "1.0.0")
        bump_type: "major", "minor", or "patch"

    Returns:
        New version string

    Raises:
        ValueError: if version_str is not valid semver or bump_type is unknown
    """
    match = _SEMVER_RE.match(version_str)
    if not match:
        raise ValueError(f"Invalid semver: '{version_str}'")

    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump type: '{bump_type}'")

    return f"{major}.{minor}.{patch}"


def _read_current_version(filepath):
    """Read and return (old_version, schema_type) from file, or sys.exit(1)."""
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found", file=sys.stderr)
        sys.exit(1)

    schema_type = detect_schema_type(filepath)
    if not schema_type:
        print(f"Error: cannot detect schema type from '{filepath}'", file=sys.stderr)
        sys.exit(1)

    data, _ = read_frontmatter(filepath)
    if not data:
        print(f"Error: no frontmatter found in {filepath}", file=sys.stderr)
        sys.exit(1)

    old_version = data.get("version")
    if old_version is None:
        print(f"Error: no 'version' field in frontmatter of {filepath}", file=sys.stderr)
        sys.exit(1)

    return str(old_version), schema_type


def _write_version(filepath, schema_type, new_version):
    """Write new version to frontmatter with last_updated, or sys.exit(1)."""
    updates = {"version": new_version}
    schema = SCHEMAS.get(schema_type, {})
    if "last_updated" in schema:
        updates["last_updated"] = date.today().isoformat()

    try:
        update_frontmatter(filepath, updates, schema_type)
    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_bump(args):
    """Read version from file frontmatter, bump it, write back."""
    old_version, schema_type = _read_current_version(args.file)

    try:
        new_version = bump_version(old_version, args.bump_type)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    _write_version(args.file, schema_type, new_version)

    json.dump({"old_version": old_version, "new_version": new_version}, sys.stdout, indent=2)
    print()


def cmd_set(args):
    """Set version to an explicit value."""
    if not _SEMVER_RE.match(args.version):
        print(f"Error: Invalid semver: '{args.version}'", file=sys.stderr)
        sys.exit(1)

    old_version, schema_type = _read_current_version(args.file)

    if old_version == args.version:
        print(f"Warning: version already set to {args.version}", file=sys.stderr)
        json.dump({"old_version": old_version, "new_version": args.version, "no_change": True}, sys.stdout, indent=2)
        print()
        sys.exit(0)

    _write_version(args.file, schema_type, args.version)

    json.dump({"old_version": old_version, "new_version": args.version}, sys.stdout, indent=2)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Test plan version management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # bump
    p_bump = subparsers.add_parser("bump", help="Bump version in file frontmatter")
    p_bump.add_argument("file", help="Path to the markdown file")
    p_bump.add_argument("bump_type", choices=["major", "minor", "patch"], help="Version part to bump")
    p_bump.set_defaults(func=cmd_bump)

    # set
    p_set = subparsers.add_parser("set", help="Set version to a specific value")
    p_set.add_argument("file", help="Path to the markdown file")
    p_set.add_argument("version", help="Version string (e.g. 2.0.0)")
    p_set.set_defaults(func=cmd_set)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
