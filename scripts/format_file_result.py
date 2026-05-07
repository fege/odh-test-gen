#!/usr/bin/env python3
"""Format test file generation result as JSON."""
import json
import sys
from pathlib import Path


def format_file_result(metadata: dict) -> str:
    """
    Format test file generation result as JSON.

    Args:
        metadata: Dict with file_index, file_path, tc_ids, functions, quality_summary, draft_files, errors

    Returns:
        JSON string with complete result including file content
    """
    file_index = metadata['file_index']
    test_file = Path(f"/tmp/test_file_{file_index}.py")

    if not test_file.exists():
        raise FileNotFoundError(f"Generated test file not found: {test_file}")

    content = test_file.read_text()

    result = {
        "file_path": metadata['file_path'],
        "content": content,
        "test_cases": metadata['tc_ids'],
        "functions": metadata['functions'],
        "quality_summary": metadata['quality_summary'],
        "draft_files": metadata.get('draft_files', []),
        "errors": metadata.get('errors', [])
    }

    return json.dumps(result, indent=2)


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/format_file_result.py <metadata.json|-}",
              file=sys.stderr)
        sys.exit(1)

    metadata_file = sys.argv[1]

    try:
        # Read metadata from file or stdin
        if metadata_file == '-':
            metadata = json.load(sys.stdin)
        else:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)

        result = format_file_result(metadata)
        print(result)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
