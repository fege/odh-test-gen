#!/usr/bin/env python3
"""CLI for reading, writing, and validating test-plan artifact frontmatter.

Skills call this script instead of writing YAML by hand, ensuring
schema-validated frontmatter on all test plan artifacts.

Supported artifact types (auto-detected from filename):
    - test-plan:        TestPlan.md files
    - test-case:        TC-*.md files
    - test-gaps:        TestPlanGaps.md files
    - test-plan-review: TestPlanReview.md files

Usage:
    # Show schema for a file type
    python3 scripts/frontmatter.py schema test-plan
    python3 scripts/frontmatter.py schema test-case
    python3 scripts/frontmatter.py schema test-gaps

    # Set/update frontmatter on a file (validates before writing)
    python3 scripts/frontmatter.py set mcp_catalog/TestPlan.md \
        feature="MCP Catalog" source_key=RHAISTRAT-400 version=1.0.0 \
        status=Draft author="QA Team"

    python3 scripts/frontmatter.py set mcp_catalog/test_cases/TC-API-001.md \
        test_case_id=TC-API-001 source_key=RHAISTRAT-400 \
        priority=P0 status=Draft

    python3 scripts/frontmatter.py set mcp_catalog/TestPlanGaps.md \
        feature="MCP Catalog" source_key=RHAISTRAT-400 \
        status=Open gap_count=3

    # Read and validate frontmatter from a file (all fields as JSON)
    python3 scripts/frontmatter.py read mcp_catalog/TestPlan.md

    # Read a single field value
    python3 scripts/frontmatter.py read mcp_catalog/TestPlan.md source_key

    # Validate frontmatter without modifying the file
    python3 scripts/frontmatter.py validate mcp_catalog/TestPlan.md
"""

import argparse
import json
import os
import sys
from datetime import date

from scripts.utils.schemas import (
    SCHEMAS,
    ValidationError,
    detect_schema_type,
    get_schema_yaml,
)
from scripts.utils.frontmatter_utils import (
    fix_markdown_body,
    lint_markdown_body,
    read_frontmatter,
    read_frontmatter_validated,
    update_frontmatter,
    write_frontmatter,
)


def _coerce_value(value_str, field_spec):
    """Coerce a CLI string value to the correct type based on field spec."""
    field_type = field_spec.get("type", "string")

    if field_type == "bool":
        if value_str.lower() in ("true", "1", "yes"):
            return True
        if value_str.lower() in ("false", "0", "no"):
            return False
        raise ValueError(f"Cannot convert '{value_str}' to bool")

    if field_type == "int":
        return int(value_str)

    if field_type == "list":
        if value_str.lower() in ("null", "none", "[]"):
            return []
        return [v.strip() for v in value_str.split(",") if v.strip()]

    if field_type == "string":
        if value_str.lower() in ("null", "none"):
            return None
        return value_str

    return value_str


def cmd_schema(args):
    """Print the schema for a file type."""
    try:
        yaml_str = get_schema_yaml(args.schema_type)
        print(yaml_str)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_read(args):
    """Read and display frontmatter from a file."""
    if not os.path.exists(args.file):
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    schema_type = args.schema_type or detect_schema_type(args.file)
    if not schema_type:
        print(f"Error: cannot detect schema type from '{args.file}'. "
              f"Use --schema-type.", file=sys.stderr)
        sys.exit(1)

    try:
        data, _ = read_frontmatter_validated(args.file, schema_type)
    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.field:
        if args.field not in data:
            print(f"Error: field '{args.field}' not found in "
                  f"frontmatter", file=sys.stderr)
            sys.exit(1)
        print(data[args.field])
    else:
        json.dump(data, sys.stdout, indent=2, default=str)
        print()


def cmd_set(args):
    """Set/update frontmatter fields on a file."""
    schema_type = args.schema_type or detect_schema_type(args.file)
    if not schema_type:
        print(f"Error: cannot detect schema type from '{args.file}'. "
              f"Use --schema-type.", file=sys.stderr)
        sys.exit(1)

    schema = SCHEMAS[schema_type]

    data = {}
    for field_value in args.fields:
        if "=" not in field_value:
            print(f"Error: expected field=value, got '{field_value}'",
                  file=sys.stderr)
            sys.exit(1)

        field_name, value_str = field_value.split("=", 1)

        if field_name == "version":
            print("Error: use scripts/version.py to manage versions",
                  file=sys.stderr)
            sys.exit(1)

        if "." in field_name:
            parent, child = field_name.split(".", 1)
            if parent not in schema:
                print(f"Error: unknown field '{parent}' for schema "
                      f"'{schema_type}'", file=sys.stderr)
                sys.exit(1)
            parent_spec = schema[parent]
            if parent_spec.get("type") != "dict" or "fields" not in parent_spec:
                print(f"Error: field '{parent}' does not support "
                      f"sub-fields", file=sys.stderr)
                sys.exit(1)
            if child not in parent_spec["fields"]:
                print(f"Error: unknown sub-field '{child}' for "
                      f"'{parent}'", file=sys.stderr)
                sys.exit(1)
            if parent not in data:
                data[parent] = {}
            data[parent][child] = _coerce_value(
                value_str, parent_spec["fields"][child])
        else:
            if field_name not in schema:
                print(f"Error: unknown field '{field_name}' for schema "
                      f"'{schema_type}'", file=sys.stderr)
                sys.exit(1)
            data[field_name] = _coerce_value(value_str, schema[field_name])

    # Auto-set last_updated if not explicitly provided and schema has it
    if "last_updated" in schema and "last_updated" not in data:
        data["last_updated"] = date.today().isoformat()

    if os.path.exists(args.file):
        try:
            update_frontmatter(args.file, data, schema_type)
        except ValidationError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            write_frontmatter(args.file, data, schema_type)
        except ValidationError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"OK: {args.file}")


def _resolve_config_path(config_file):
    """Resolve the markdownlint config path, falling back to repo root."""
    if config_file:
        return config_file
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(repo_root, ".markdownlint.yaml")
    if os.path.exists(candidate):
        return candidate
    return None


def _print_violations(filepath, failures):
    """Print lint violations to stderr."""
    for violation in failures:
        extra = (f" [{violation['extra_info']}]"
                 if violation["extra_info"] else "")
        print(f"{filepath}:{violation['line']}:{violation['column']} "
              f"{violation['rule_id']}/{violation['rule_name']} "
              f"{violation['description']}{extra}", file=sys.stderr)
    print(f"FAIL: {filepath} ({len(failures)} violation(s))",
          file=sys.stderr)


def _load_body_for_lint(args):
    """Validate file exists, resolve config, and read the markdown body.

    Returns (config_path, body) or exits/returns None on empty body.
    """
    if not os.path.exists(args.file):
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    config_path = _resolve_config_path(args.config_file)

    _, body = read_frontmatter(args.file)
    if not body.strip():
        print(f"OK: {args.file} (no markdown body)")
        return None, None

    return config_path, body


def cmd_lint(args):
    """Lint the markdown body of a file using pymarkdownlnt."""
    config_path, body = _load_body_for_lint(args)
    if body is None:
        return

    failures = lint_markdown_body(body, config_path=config_path)
    if not failures:
        print(f"OK: {args.file}")
        return

    _print_violations(args.file, failures)
    sys.exit(1)


def cmd_fix(args):
    """Auto-fix markdown lint violations where supported."""
    config_path, body = _load_body_for_lint(args)
    if body is None:
        return

    with open(args.file, encoding="utf-8") as f:
        original = f.read()

    fixed_body, was_fixed = fix_markdown_body(body, config_path=config_path)

    if not was_fixed:
        remaining = lint_markdown_body(body, config_path=config_path)
        if remaining:
            _print_violations(args.file, remaining)
            sys.exit(1)
        print(f"OK: {args.file} (nothing to fix)")
        return

    content = original.replace(body, fixed_body, 1)
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(content)

    remaining = lint_markdown_body(fixed_body, config_path=config_path)
    print(f"FIXED: {args.file}")
    if remaining:
        _print_violations(args.file, remaining)
        sys.exit(1)


def cmd_validate(args):
    """Validate frontmatter without modifying the file."""
    if not os.path.exists(args.file):
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    schema_type = args.schema_type or detect_schema_type(args.file)
    if not schema_type:
        print(f"Error: cannot detect schema type from '{args.file}'. "
              f"Use --schema-type.", file=sys.stderr)
        sys.exit(1)

    try:
        read_frontmatter_validated(args.file, schema_type)
        print(f"OK: {args.file}")
    except ValidationError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Test plan artifact frontmatter CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schema
    p_schema = subparsers.add_parser("schema",
                                     help="Show schema for a file type")
    p_schema.add_argument("schema_type",
                          choices=list(SCHEMAS.keys()),
                          help="Schema type to display")
    p_schema.set_defaults(func=cmd_schema)

    # read
    p_read = subparsers.add_parser("read",
                                   help="Read frontmatter from a file")
    p_read.add_argument("file", help="Path to the markdown file")
    p_read.add_argument("field", nargs="?", default=None,
                        help="Single field name to extract (omit for all)")
    p_read.add_argument("--schema-type", dest="schema_type",
                        choices=list(SCHEMAS.keys()),
                        help="Schema type (auto-detected from filename)")
    p_read.set_defaults(func=cmd_read)

    # set
    p_set = subparsers.add_parser(
        "set", help="Set/update frontmatter fields")
    p_set.add_argument("file", help="Path to the markdown file")
    p_set.add_argument("fields", nargs="+",
                       help="Fields as field=value pairs")
    p_set.add_argument("--schema-type", dest="schema_type",
                       choices=list(SCHEMAS.keys()),
                       help="Schema type (auto-detected from filename)")
    p_set.set_defaults(func=cmd_set)

    # lint
    p_lint = subparsers.add_parser("lint",
                                   help="Lint markdown body")
    p_lint.add_argument("file", help="Path to the markdown file")
    p_lint.add_argument("--config", dest="config_file", default=None,
                        help="Path to .markdownlint.yaml config "
                             "(default: auto-detect in repo root)")
    p_lint.set_defaults(func=cmd_lint)

    # fix
    p_fix = subparsers.add_parser("fix",
                                  help="Auto-fix markdown lint violations")
    p_fix.add_argument("file", help="Path to the markdown file")
    p_fix.add_argument("--config", dest="config_file", default=None,
                       help="Path to .markdownlint.yaml config "
                            "(default: auto-detect in repo root)")
    p_fix.set_defaults(func=cmd_fix)

    # validate
    p_validate = subparsers.add_parser("validate",
                                       help="Validate frontmatter")
    p_validate.add_argument("file", help="Path to the markdown file")
    p_validate.add_argument("--schema-type", dest="schema_type",
                            choices=list(SCHEMAS.keys()),
                            help="Schema type (auto-detected from filename)")
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
