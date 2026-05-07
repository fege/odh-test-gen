#!/usr/bin/env python3
"""
List test functions from a Python test file.

Extracts test function names, line numbers, and docstrings using AST parsing.
Used for detecting already-implemented tests.

Usage:
    python scripts/list_test_functions.py <test_file.py>

Output (JSON):
    {
        "file": "tests/test_example.py",
        "functions": [
            {
                "name": "test_create_notebook",
                "line": 42,
                "docstring": "Test notebook creation via API."
            }
        ]
    }
"""

import ast
import json
import sys
from pathlib import Path


def list_test_functions(file_path: str) -> str:
    """
    List all test functions in a Python file.

    Args:
        file_path: Path to Python test file

    Returns:
        JSON string with function metadata

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read and parse file
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=str(file_path_obj))
    except SyntaxError:
        # If file has syntax errors, return empty list with error flag
        return json.dumps({
            'file': str(file_path_obj),
            'functions': [],
            'parse_error': True
        }, indent=2)

    # Extract test functions (only top-level, starting with 'test_')
    functions = [
        {
            'name': node.name,
            'line': node.lineno,
            'docstring': ast.get_docstring(node),
        }
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')
    ]

    return json.dumps({
        'file': str(file_path_obj),
        'functions': functions,
    }, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/list_test_functions.py <test_file.py>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        result = list_test_functions(file_path)
        print(result)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
