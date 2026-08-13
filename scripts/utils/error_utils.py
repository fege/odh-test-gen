#!/usr/bin/env python3


import json
import sys


def exit_error(message: str) -> None:
    """Print error message to stderr and exit with code 1."""
    print(message, file=sys.stderr)
    sys.exit(1)


def exit_graceful(message: str) -> None:
    """Print error message to stderr and exit with code 0 (graceful fail for skill context)."""
    print(message, file=sys.stderr)
    sys.exit(0)


def exit_error_multiline(lines: list[str]) -> None:
    """Print multiple error lines to stderr and exit with code 1."""
    for line in lines:
        print(line, file=sys.stderr)
    sys.exit(1)


def exit_error_with_json(
    json_output: dict | None = None, message: str = "", error_key: str = "", indent: int | None = 2
) -> None:
    """Print JSON response to stdout and exit with code 1.

    Optionally prints a human-readable message to stderr first.

    Can be called as:
    - exit_error_with_json(json_output_dict) — uses provided dict as-is
    - exit_error_with_json(message="msg", error_key="code") — builds {"error": "code"} dict
    - exit_error_with_json(json_output_dict, message="msg") — uses dict + optional message

    Args:
        json_output: Dict to serialize and print to stdout (alternative to error_key)
        message: Optional human-readable message printed to stderr
        error_key: Machine-readable error code (used to build JSON if json_output not provided)
        indent: JSON indentation level (default 2, set to None for compact)
    """
    if message:
        print(message, file=sys.stderr)

    if json_output is None:
        json_output = {"error": error_key} if error_key else {}

    print(json.dumps(json_output, indent=indent))
    sys.exit(1)
