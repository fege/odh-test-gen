#!/usr/bin/env python3
"""
Parse skill arguments to extract flags and values.

Usage:
    python scripts/parse_skill_args.py --flag-name <args_string>

Returns the value after --flag-name, or empty string if not found.
"""

import re
import sys

from scripts.utils.error_utils import exit_error


def extract_flag_value(args_string: str, flag_name: str) -> str:
    """
    Extract value for a flag from arguments string.

    Args:
        args_string: Full arguments string
        flag_name: Flag name (without -- prefix)

    Returns:
        Flag value if found, empty string otherwise

    Examples:
        >>> extract_flag_value("path --test-cases TC-001,TC-002", "test-cases")
        'TC-001,TC-002'
        >>> extract_flag_value("path --target-repo ~/repo --other", "target-repo")
        '~/repo'
        >>> extract_flag_value("path only", "test-cases")
        ''
    """
    if not args_string:
        return ""

    flag_pattern = f"--{flag_name}"
    if flag_pattern not in args_string:
        return ""

    # Match --flag-name followed by value (stops at next -- or end of string)
    # Value can contain hyphens (e.g., TC-NEG-001)
    pattern = rf"--{re.escape(flag_name)}\s+([^\s]+?)(?:\s+--|$)"
    match = re.search(pattern, args_string)

    if match:
        return match.group(1).strip()

    return ""


def main():
    """CLI entry point."""
    if len(sys.argv) != 3 or not sys.argv[1].startswith("--"):
        exit_error("Usage: python scripts/parse_skill_args.py --flag-name <args_string>")

    flag_name = sys.argv[1][2:]
    args_string = sys.argv[2]

    value = extract_flag_value(args_string, flag_name)

    # For test-cases flag, convert comma-separated to space-separated
    if flag_name == "test-cases" and value:
        value = value.replace(",", " ")

    print(value)


if __name__ == "__main__":
    main()
