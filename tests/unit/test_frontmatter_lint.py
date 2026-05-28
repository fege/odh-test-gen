"""Unit tests for the markdown lint functionality."""

import os
import tempfile

import pytest
from pymarkdown.api import PyMarkdownApi

from scripts.utils.frontmatter_utils import (
    configure_pymarkdown,
    fix_markdown_body,
    lint_markdown_body,
    load_markdownlint_config,
)


CLEAN_MARKDOWN = """\
# Heading

Some paragraph text here.

## Second Heading

- Item one
- Item two

Another paragraph.
"""

DIRTY_MARKDOWN = """\
# Heading
No blank line after heading.
- list without surrounding blank lines
"""

LONG_LINE_MARKDOWN = """\
# Heading

This line is fine.

This line is way too long and exceeds one hundred characters which should trigger the MD013 line length rule for sure yes.
"""

FRONTMATTER_AND_BODY = """\
---
feature: Test Feature
source_key: RHAISTRAT-999
---
# Test Plan

Some content here.
"""


class TestLoadMarkdownlintConfig:
    def test_loads_valid_config(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as config_file:
            config_file.write("MD013:\n  line_length: 120\nMD036: false\n")
            config_file.flush()
            config = load_markdownlint_config(config_file.name)

        os.unlink(config_file.name)
        assert config["MD013"]["line_length"] == 120
        assert config["MD036"] is False

    def test_returns_empty_for_missing_file(self):
        config = load_markdownlint_config("/nonexistent/path.yaml")
        assert config == {}

    def test_returns_empty_for_non_dict(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as config_file:
            config_file.write("- just\n- a\n- list\n")
            config_file.flush()
            config = load_markdownlint_config(config_file.name)

        os.unlink(config_file.name)
        assert config == {}


class TestConfigurePymarkdown:
    def test_disables_rule_when_false(self):
        api = PyMarkdownApi()
        configure_pymarkdown(api, {"MD036": False})
        result = api.scan_string(
            "# Heading\n\n**not a real heading**\n"
        )
        md036_failures = [
            f for f in result.scan_failures if f.rule_id == "MD036"
        ]
        assert len(md036_failures) == 0

    def test_sets_integer_property(self):
        api = PyMarkdownApi()
        configure_pymarkdown(api, {"MD013": {"line_length": 200}})
        long_line = "# Heading\n\n" + "a" * 150 + "\n"
        result = api.scan_string(long_line)
        md013_failures = [
            f for f in result.scan_failures if f.rule_id == "MD013"
        ]
        assert len(md013_failures) == 0


class TestLintMarkdownBody:
    def test_clean_markdown_passes(self):
        failures = lint_markdown_body(CLEAN_MARKDOWN)
        assert failures == []

    def test_dirty_markdown_reports_violations(self):
        failures = lint_markdown_body(DIRTY_MARKDOWN)
        assert len(failures) > 0
        rule_ids = {f["rule_id"] for f in failures}
        assert rule_ids & {"MD022", "MD032"}

    def test_failure_dict_has_expected_keys(self):
        failures = lint_markdown_body(DIRTY_MARKDOWN)
        assert len(failures) > 0
        expected_keys = {
            "line", "column", "rule_id", "rule_name",
            "description", "extra_info",
        }
        assert set(failures[0].keys()) == expected_keys

    def test_config_changes_behavior(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as config_file:
            config_file.write("MD013:\n  line_length: 200\n")
            config_file.flush()
            failures = lint_markdown_body(
                LONG_LINE_MARKDOWN, config_path=config_file.name)

        os.unlink(config_file.name)
        md013_failures = [
            failure for failure in failures
            if failure["rule_id"] == "MD013"
        ]
        assert len(md013_failures) == 0

    def test_body_after_frontmatter_is_clean(self):
        body = FRONTMATTER_AND_BODY.split("---\n", 2)[2]
        failures = lint_markdown_body(body)
        assert failures == []


TRAILING_SPACES_MARKDOWN = "# Heading\n\nSome text \nMore text.\n"

MISSING_TRAILING_NEWLINE = "# Heading\n\nSome text."


class TestFixMarkdownBody:
    def test_fixes_trailing_spaces(self):
        fixed, was_fixed = fix_markdown_body(TRAILING_SPACES_MARKDOWN)
        assert was_fixed
        assert "text \n" not in fixed

    def test_fixes_missing_trailing_newline(self):
        fixed, was_fixed = fix_markdown_body(MISSING_TRAILING_NEWLINE)
        assert was_fixed
        assert fixed.endswith("\n")

    def test_clean_markdown_unchanged(self):
        fixed, was_fixed = fix_markdown_body(CLEAN_MARKDOWN)
        assert not was_fixed
        assert fixed == CLEAN_MARKDOWN

    def test_unfixable_violations_remain(self):
        fixed, _was_fixed = fix_markdown_body(DIRTY_MARKDOWN)
        remaining = lint_markdown_body(fixed)
        unfixable_ids = {
            failure["rule_id"] for failure in remaining
        }
        assert unfixable_ids & {"MD022", "MD032"}
