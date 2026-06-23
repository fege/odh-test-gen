"""
Frontmatter read/write/validate operations for test plan artifacts.

Handles YAML frontmatter in markdown files (between --- delimiters).
Uses schemas.py for validation.
"""

import re
import sys

try:
    import yaml
except ImportError:
    print(
        "Error: PyYAML is required but not installed.\nInstall it with: uv sync",
        file=sys.stderr,
    )
    sys.exit(1)

from pymarkdown.api import PyMarkdownApi

from .schemas import ValidationError, validate, apply_defaults


# ─── Frontmatter Read/Write ────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)


def read_frontmatter(path):
    """Read and parse YAML frontmatter from a markdown file.

    Returns:
        (data_dict, body_string) — frontmatter as dict, remainder as string.
        Returns ({}, full_content) if no frontmatter found.
    """
    with open(path, encoding="utf-8") as f:
        content = f.read()

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    yaml_str = match.group(1)
    body = content[match.end() :]

    data = yaml.safe_load(yaml_str)
    if not isinstance(data, dict):
        return {}, content

    return data, body


def read_frontmatter_validated(path, schema_type):
    """Read frontmatter and validate against schema.

    Returns:
        (data_dict, body_string)

    Raises:
        ValidationError: if frontmatter fails validation
        FileNotFoundError: if file doesn't exist
    """
    data, body = read_frontmatter(path)
    if not data:
        raise ValidationError(f"No frontmatter found in {path}")

    errors = validate(data, schema_type)
    if errors:
        raise ValidationError(f"Frontmatter validation failed in {path}:\n" + "\n".join(f"  - {e}" for e in errors))

    return data, body


def write_frontmatter(path, data, schema_type):
    """Write frontmatter to a markdown file.

    Validates data against schema, writes frontmatter + body.

    Args:
        path: file path (must exist if preserving body, or new file)
        data: frontmatter dict
        schema_type: schema to validate against

    Raises:
        ValidationError: if data fails validation
    """
    apply_defaults(data, schema_type)
    errors = validate(data, schema_type)
    if errors:
        raise ValidationError("Frontmatter validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    # Try to preserve existing body
    try:
        _, body = read_frontmatter(path)
    except FileNotFoundError:
        body = ""

    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    content = f"---\n{yaml_str}---\n{body}"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def update_frontmatter(path, updates, schema_type):
    """Update specific frontmatter fields in an existing file.

    Reads existing frontmatter, merges updates (overwriting on conflict),
    validates, and writes back.

    Args:
        path: file path (must exist)
        updates: dict of fields to add/update
        schema_type: schema to validate against

    Raises:
        ValidationError: if merged data fails validation
        FileNotFoundError: if file doesn't exist
    """
    data, body = read_frontmatter(path)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key].update(value)
        else:
            data[key] = value

    apply_defaults(data, schema_type)
    errors = validate(data, schema_type)
    if errors:
        raise ValidationError(
            f"Frontmatter validation failed after update in {path}:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    content = f"---\n{yaml_str}---\n{body}"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ─── Markdown Linting ─────────────────────────────────────────────────────────


def load_markdownlint_config(config_path):
    """Load rules from a .markdownlint.yaml config file."""
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config if isinstance(config, dict) else {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}


def configure_pymarkdown(api, config):
    """Translate .markdownlint.yaml config into PyMarkdownApi settings."""
    for rule_id, rule_config in config.items():
        rule_lower = rule_id.lower()

        if rule_config is False:
            api.disable_rule_by_identifier(rule_lower)
            continue

        if isinstance(rule_config, dict):
            for prop, value in rule_config.items():
                key = f"plugins.{rule_lower}.{prop}"
                if isinstance(value, bool):
                    api.set_boolean_property(key, value)
                elif isinstance(value, int):
                    api.set_integer_property(key, value)
                else:
                    api.set_string_property(key, str(value))


def lint_markdown_body(body, config_path=None):
    """Lint markdown content using pymarkdownlnt.

    Args:
        body: markdown string to lint (frontmatter already stripped).
        config_path: optional path to .markdownlint.yaml config file.

    Returns:
        list of failure dicts with keys: line, column, rule_id,
        rule_name, description, extra_info.
    """
    api = PyMarkdownApi()

    if config_path:
        config = load_markdownlint_config(config_path)
        configure_pymarkdown(api, config)

    result = api.scan_string(body)

    return [
        {
            "line": f.line_number,
            "column": f.column_number,
            "rule_id": f.rule_id,
            "rule_name": f.rule_name,
            "description": f.rule_description,
            "extra_info": f.extra_error_information or "",
        }
        for f in result.scan_failures
    ]


def fix_markdown_body(body, config_path=None):
    """Auto-fix markdown content where supported by pymarkdownlnt.

    Args:
        body: markdown string to fix (frontmatter already stripped).
        config_path: optional path to .markdownlint.yaml config file.

    Returns:
        (fixed_body, was_fixed) — the corrected string and whether
        any changes were made.
    """
    api = PyMarkdownApi()

    if config_path:
        config = load_markdownlint_config(config_path)
        configure_pymarkdown(api, config)

    result = api.fix_string(body)
    return result.fixed_file, result.was_fixed
