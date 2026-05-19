# Changelog

All notable changes to the test-plan plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Jira integration**: Replaced MCP calls with direct Python scripts for improved cost efficiency and reliability ([#18](https://github.com/opendatahub-io/odh-test-gen/issues/18))
  - Added `scripts/jira_utils.py` - Jira REST API client with retry logic, proper 204 No Content handling, and deterministic label ordering
  - Added `scripts/fetch_issue.py` - CLI tool for fetching issues and converting to markdown
  - Added `scripts/add_jira_labels.py` - Safe CLI wrapper for adding labels (replaces fragile shell string manipulation)
  - Updated skills (`test-plan-create`, `test-plan-review`, `test-plan-score`) to use environment variables (`JIRA_URL`, `JIRA_USER`, `JIRA_TOKEN`) instead of MCP server
  - No MCP server setup required - works with standard Jira API tokens
  - Prevents unnecessary API calls by detecting when labels haven't changed

## [1.0.0] - 2026-05-06

### Breaking Changes

#### Plugin Structure Migration
- **Plugin format**: Migrated to Claude Code v1.0.0 plugin specification
  - Added `.claude-plugin/plugin.json` with plugin metadata
  - Skills directory: `.claude/skills/` → `skills/` (root level)
  - Enables proper plugin installation and marketplace distribution

#### Skill Naming Convention
All skill names changed from dot notation to hyphen notation:

| Old Name (0.x) | New Name (1.0.0) |
|----------------|------------------|
| `/test-plan.create` | `/test-plan-create` |
| `/test-plan.create-cases` | `/test-plan-create-cases` |
| `/test-plan.update` | `/test-plan-update` |
| `/test-plan.case-implement` | `/test-plan-case-implement` |
| `/test-plan.publish` | `/test-plan-publish` |
| `/test-plan.resolve-feedback` | `/test-plan-resolve-feedback` |
| `/test-plan.score` | `/test-plan-score` |
| `/test-plan.ui-verify` | `/test-plan-ui-verify` |

Internal skills (analyzers, merge, review, etc.) similarly renamed.

### Migration Guide

#### For End Users (Marketplace Installation)
**No action required!** Reinstall from marketplace:
```bash
/plugin install test-plan@opendatahub-skills
```

The new version uses hyphenated names automatically.

#### For Contributors (Local Development)
1. Pull the latest `main` branch
2. Update slash commands in your workflows (dots → hyphens)
3. Install dependencies: `uv pip install -e ".[dev]"`

**Note:** Your existing test plan artifacts (TestPlan.md, test cases) remain fully compatible.

### Added

- **Comprehensive test coverage**: 204 unit and integration tests (up from 146)
- **Python scripts**: 22 tested scripts extract procedural logic from bash (~500 lines eliminated)
- **Trigger phrases**: All skill descriptions include "Use when..." phrases for better discoverability
- **Quality assurance**: Auto-revision workflow for test plans and generated code
- **Parallel execution**: Analyzer and test generation workflows run in parallel
- **odh-test-context integration**: Automatic detection of repository testing conventions

### Changed

#### Architecture Improvements
- **Simplified code generation**: Unified test file generator (replaced 2 nested skills with 1)
  - Reduced complexity: 3-level nesting → 2-level orchestration
  - Net reduction: -261 lines of code
  - Clearer separation of concerns

- **test-plan-case-implement refactored**: 1040 → 540 lines (-48% reduction)
  - Extracted deterministic logic to tested Python scripts
  - Improved maintainability and testability

- **Sub-agent orchestration standardized**: 
  - 9 internal skills for modular workflows
  - Clean isolation with `context: fork` pattern
  - Enables parallel execution where possible

- **Script-based workflow**: 
  - Scripts output JSON (no shell parsing needed)
  - Deterministic operations use Python (not bash + LLM)
  - All scripts have unit tests

### Removed

- Old plugin structure in `.claude/skills/` (migrated to `skills/`)
- Nested code generation skills (consolidated into unified generator)

---

## [0.x] - Pre-v1.0.0

Previous versions used dot notation (`test-plan.create`) and lived in `.claude/skills/`. 

See git history before tag `pre-v1-migration` for details.

---

## Upgrade Notes

### Compatibility
- ✅ **Test plan artifacts**: Fully compatible (no frontmatter schema changes)
- ✅ **Workflows**: Unchanged behavior (only command names changed)
- ✅ **Dependencies**: Same prerequisites (Claude Code, uv, Python 3.10+)

### What Changed for Users
- **Slash commands**: Use hyphens instead of dots
- **Installation**: Proper marketplace support
- **Everything else**: Works the same way

### What Changed for Developers
- **Directory structure**: `skills/` at root level
- **Skill names**: Hyphens throughout
- **Testing**: Extensive test suite with 204 tests
- **Architecture**: Cleaner orchestration with forked sub-agents

---

## Links
- [Repository](https://github.com/opendatahub-io/odh-test-gen)
- [Skills Registry](https://github.com/opendatahub-io/skills-registry)
- [Bug Reports](https://github.com/opendatahub-io/odh-test-gen/issues)
