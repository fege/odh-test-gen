# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Claude Code plugin (`test-plan`) that provides skills for end-to-end test planning for RHOAI (Red Hat OpenShift AI). Skills generate test plans from Jira strategies, create test cases, implement executable automation code, verify UI tests via Playwright, publish to GitHub, and score quality. The plugin is distributed via the opendatahub-io/skills-registry marketplace.

## Build & Test Commands

```bash
uv sync --extra dev          # Install dependencies (editable mode)
uv run pytest tests/ -v      # Run all tests
uv run pytest tests/unit/ -v # Run unit tests only
uv run pytest tests/integration/ -v  # Run integration tests only
uv run pytest tests/unit/test_schema_validation.py -v  # Run one test file
uv run pytest tests/unit/test_schema_validation.py::TestPlanSchemaValidation::test_field_validation -v  # Run one test
uv run pytest tests/ -v --cov=scripts --cov-report=term-missing  # With coverage
make lint                    # Run skillsaw linter
make skillsaw-fix            # Auto-fix skillsaw issues
```

CI enforces `--cov-fail-under=65` for test coverage.

## Architecture

**Plugin structure**: `.claude-plugin/plugin.json` defines the plugin. Each skill lives in `skills/<skill-name>/SKILL.md`. Skills share Python utilities via `skills/_common/scripts` which is a symlink to the top-level `scripts/` directory.

**Design principle**: Procedural logic is extracted to deterministic Python scripts in `scripts/` (no LLM calls). Scripts output JSON, not text. LLMs are only used for semantic work (analyzing requirements, writing test code, quality scoring).

**Sub-agent orchestration**: 8 internal skills use `context: fork` for clean isolation and parallel execution. 1 skill (review) runs in-parent context to write persistent files. All are invoked via the Skill tool.

**Key directories**:
- `scripts/` — Python modules for deterministic operations (validation, parsing, AST extraction, Jira API)
- `scripts/utils/` — Shared utilities (schemas, frontmatter, repo discovery, component mapping)
- `skills/` — SKILL.md files defining each skill's behavior
- `tests/unit/` — Fast isolated unit tests
- `tests/integration/` — Tests involving subprocess calls and file I/O

## Linting

Pre-commit hooks enforce code quality (run `pre-commit run --all-files` or let git hooks trigger automatically):
- **ruff** — linting and formatting (config in `pyproject.toml`, 120-char line length)
- **flake8** — with RedHatQE plugins UUC (unused-unique-constants) and UFN (unique-function-names); config in `.flake8`
- **Standard hooks** — check-merge-conflict, debug-statements, trailing-whitespace, end-of-file-fixer, check-ast, check-builtin-literals, check-toml

CI runs pre-commit and skillsaw on every PR via `.github/workflows/lint.yml`.

Skillsaw lints skill files for context budget (warn at 6000 tokens, error at 8000), content positioning, and placeholder text. Config is in `.skillsaw.yaml` with strict mode enabled.

Markdown linting uses pymarkdownlnt with config in `.markdownlint.yaml` (100-char line length, some rules disabled).

## Environment Variables

- `JIRA_URL`, `JIRA_USER`, `JIRA_TOKEN` — Required for Jira integration
- `CLAUDE_NON_INTERACTIVE=true` — Skip interactive prompts (CI mode)

## Artifact Separation

Test plan artifacts (TestPlan.md, TC-*.md files) are written to a separate directory (default `~/Code/opendatahub-test-plans/plans/`), never into this skill repository. The `--output-dir .` flag overrides this for contributor testing.
