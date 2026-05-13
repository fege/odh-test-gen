# Test Plan

End-to-end test planning workflow for RHOAI: generate test plans from strategies, create test cases, implement executable automation code, verify UI tests against live clusters via Playwright, publish to GitHub with PR creation, resolve review feedback, and score quality with automated rubrics using parallel sub-agent analysis.

## Skills

### User-invocable (8 skills)

| Skill | Description |
|-------|-------------|
| `/test-plan-create` | Generate a test plan from a strategy (RHAISTRAT or RHOAIENG), with optional ADR |
| `/test-plan-create-cases` | Generate individual test case files from an existing test plan |
| `/test-plan-update` | Update test plan with new docs (ADR, API specs), re-analyze, bump version |
| `/test-plan-case-implement` | Generate executable test automation code from TC specifications with intelligent placement |
| `/test-plan-ui-verify` | Verify UI test cases from a PR against a live ODH/RHOAI cluster via Playwright |
| `/test-plan-publish` | Publish test plan artifacts to GitHub — branch, commit, and open a PR |
| `/test-plan-resolve-feedback` | Assess PR review comments, let the user decide what to apply, and push updates |
| `/test-plan-score` | Score an existing test plan using quality rubric (without auto-revision) |

### Sub-agents (9 internal skills, forked with `context: fork`)

| Skill | Description |
|-------|-------------|
| `test-plan-analyze-endpoints` | Extract feature scope, test objectives, and API endpoints from docs |
| `test-plan-analyze-risks` | Analyze strategy/ADR to determine test levels, types, priorities, risks |
| `test-plan-analyze-infra` | Identify test environment, data, infrastructure requirements |
| `test-plan-analyze-placement` | Recommend test placement (component repo vs downstream) |
| `test-plan-merge` | Intelligently merge new analyzer findings into existing test plan |
| `test-plan-resolve-gaps` | Cross-reference gaps with new findings to determine what's resolved |
| `test-plan-review` | Review test plan for completeness, consistency, and quality with auto-revision |
| `test-plan-generate-test-file` | Generate complete test file with all functions, quality scoring and auto-revision |
| `test-plan-score-test-function` | Score generated test function code using 5-criteria quality rubric |

## Installation

### Option 1: Install from Marketplace (Recommended)

Install from the [opendatahub-io/skills-registry](https://github.com/opendatahub-io/skills-registry) marketplace:

```bash
# Add the marketplace (one-time)
claude plugin marketplace add opendatahub-io/skills-registry

# Install test-plan plugin
/plugin install test-plan@opendatahub-skills
```

This clones the repository and makes skills immediately available. Then install Python dependencies:

```bash
cd ~/.claude/plugins/test-plan
uv sync --extra dev
```

Use skills:
```bash
# Will prompt for artifact location (default: ~/Code/odh-test-plans)
/test-plan-create RHAISTRAT-400

# Auto-uses location from /test-plan-create
/test-plan-create-cases

# Auto-detects feature from /test-plan-create session
# Will prompt for publish target (default: opendatahub-io/odh-test-plans)
/test-plan-publish
```

### Option 2: Manual Clone (For Contributors)

Clone the repository directly:

```bash
git clone https://github.com/opendatahub-io/odh-test-gen ~/Code/odh-test-gen
cd ~/Code/odh-test-gen
uv sync --extra dev
```

Skills are available from `skills/` directory.

**Note**: Skills use symlinks for shared utilities (`_common/scripts → ../../scripts`). Both installation methods clone the full repository, so symlinks resolve correctly.

Each skill includes an `argument-hint` field in its frontmatter for autocomplete guidance when typing slash commands.

## Artifact Location

**Important**: Test plan artifacts are kept separate from the skill repository to maintain clean boundaries between code and data.

### Default Behavior

When you run `/test-plan-create`, it asks where to save artifacts:
```text
Where should test plan artifacts be created?

Provide a directory path (e.g., ~/Code/odh-test-plans/plans/<team-name>), or press Enter for: ~/Code/odh-test-plans/plans/

Note: Replace <team-name> with your team name (e.g., ai-hub, dashboard, etc.)
```

- **QE Teams**: Provide your team's directory path (e.g., `~/Code/odh-test-plans/plans/ai-hub`)
- **Contributors**: Use default `~/Code/odh-test-plans/plans/` or any path outside the skill repo
- **Save Preference**: Optionally save your choice to `.claude/settings.json` for future runs

The skill creates: `<your-path>/<feature-name>/`  
Example: If you enter `~/Code/odh-test-plans/plans/ai-hub`, it creates `~/Code/odh-test-plans/plans/ai-hub/mcp_catalog/`

### Session Context

`/test-plan-create-cases` automatically uses the same location as `/test-plan-create` when run in the same session (no prompt needed).

### Publishing

**Fork Workflow Required**: You must work from a personal fork to contribute:

1. **Fork** `opendatahub-io/odh-test-plans` on GitHub to `your-username/odh-test-plans`
2. **Clone** your fork: `git clone https://github.com/YOUR-USERNAME/odh-test-plans ~/Code/odh-test-plans`
3. **Create** test plans with `/test-plan-create` (saved in your fork)
4. **Publish** with `/test-plan-publish`:
   - Pushes to YOUR fork
   - Creates PR from your fork → upstream `opendatahub-io/odh-test-plans`
   - The skill verifies you're working from a fork, not upstream

**Default publish target**: `opendatahub-io/odh-test-plans`

### Contributor Override

Contributors testing skills can use `--output-dir` to force creation in the current directory:
```bash
/test-plan-create RHAISTRAT-400 --output-dir .
```

**Note**: The skill repository blocks artifact creation by default to prevent mixing code and test plan data.

## Architecture

### v1.0.0 Design Principles

**Deterministic Scripts** - Procedural logic extracted to Python scripts (no LLM calls):
- Feature validation, component detection, TC filtering, file mapping
- AST-based function extraction, score parsing, frontmatter updates
- 22 tested Python scripts

**LLMs Only Where Necessary** - Semantic understanding and code generation:
- Writing test code, quality scoring, semantic function matching
- Analyzing requirements, merging findings, resolving gaps

**Sub-Agent Orchestration** - 9 internal skills:
- **Forked (8 with `context: fork`)**: Analyzers (endpoints, risks, infra, placement), workflow (merge, resolve-gaps), quality (generate-test-file, score-test-function) — clean isolation, parallel execution
- **In-parent (1 without fork)**: review — writes persistent files in parent context
- All invoked via Skill tool, deterministic return values

**No Shell Parsing** - Scripts output JSON, Claude extracts values directly (no jq commands needed)

## Usage

### Basic Workflow

**Prerequisites**: Fork and clone `opendatahub-io/odh-test-plans` first (see Publishing section above).

```bash
# 1. Generate a test plan from a Jira strategy
#    Will ask: Where to save artifacts? [~/Code/odh-test-plans/plans/]
#    Provide your team path, e.g.: ~/Code/odh-test-plans/plans/ai-hub
#    Creates: ~/Code/odh-test-plans/plans/ai-hub/<feature>/
/test-plan-create RHAISTRAT-400

# 2. Generate test cases (auto-uses location from step 1)
/test-plan-create-cases

# 3. Publish to GitHub
#    Auto-detects feature directory from /test-plan-create session
#    Verifies you're working from a fork
#    Creates PR from your-username/odh-test-plans → opendatahub-io/odh-test-plans
/test-plan-publish
```

### Advanced Options

```bash
# Generate test plan with ADR for extra technical depth
/test-plan-create RHAISTRAT-400 /path/to/adr.pdf

# Generate test cases from a GitHub PR (for /test-plan-resolve-feedback workflow)
/test-plan-create-cases https://github.com/opendatahub-io/odh-test-plans/pull/5

# Generate test cases for a specific local directory
/test-plan-create-cases ~/Code/odh-test-plans/plans/ai-hub/mcp_catalog

# Publish with specific reviewers
/test-plan-publish mcp_catalog --reviewers alice,bob

# Publish to a specific repository
/test-plan-publish mcp_catalog --repo opendatahub-io/test-plans

# Resolve PR review feedback
/test-plan-resolve-feedback https://github.com/opendatahub-io/odh-test-plans/pull/42

# Update test plan with new documentation
/test-plan-update ~/Code/odh-test-plans/plans/ai-hub/mcp_catalog adr.pdf api-spec.md

# Update test plan from GitHub PR with new docs
/test-plan-update https://github.com/opendatahub-io/odh-test-plans/pull/42 design-doc.md

# Generate executable test code from test cases
/test-plan-case-implement mcp_catalog

# Generate code for specific test cases only
/test-plan-case-implement mcp_catalog --test-cases TC-API-001,TC-API-002

# Score a test plan without triggering auto-revision
/test-plan-score mcp_catalog
```

### Contributor Workflow

```bash
# Force creation in current directory (bypasses skill repo validation)
/test-plan-create RHAISTRAT-400 --output-dir .

# Force test case creation in current directory
/test-plan-create-cases mcp_catalog --output-dir .
```

## Pipeline

```
/test-plan-create RHAISTRAT-400
        │
        ├── test-plan-analyze-endpoints  ─┐
        ├── test-plan-analyze-risks      ─┤  (parallel)
        └── test-plan-analyze-infra      ─┘
                    │
                    ▼
            TestPlan.md + TestPlanGaps.md
                    │
                    ▼
            Gap resolution (HITL)
                    │
                    ▼
            test-plan-review (auto-revision, scoring)
                    │
                    ▼
        /test-plan-create-cases (optional auto-run)
                    │
                    ▼
            TC-*.md + INDEX.md
                    │
                    ├─────────────────────┐
                    │                     │
                    ▼                     ▼
        /test-plan-publish    /test-plan-case-implement
                    │                     │
                    │                     ├── preflight.py (validation + detection)
                    │                     ├── filter_test_cases.py, map_test_files.py
                    │                     ├── test-plan-analyze-placement
                    │                     └── test-plan-generate-test-file (parallel per file)
                    │                         ├── list_test_functions.py (AST)
                    │                         ├── test-plan-score-test-function (per function)
                    │                         └── parse_test_score.py
                    │                     │
                    ▼                     ▼
            GitHub PR          Generated test code in target repos
                    │
                    ▼
            GitHub PR (with optional reviewers)
                    │
                    ├──────────────────────────────────────┐
                    │                                      │
                    ▼                                      ▼
        /test-plan-resolve-feedback          /test-plan-update (new docs)
        (after PR reviews)                    │
                    │                         ├── re-run analyzers
                    │                         ├── update TestPlan.md
                    │                         ├── test-plan-review
                    │                         └── optionally regenerate test cases
                    │                         │
                    ▼                         ▼
            Updated artifacts ◄───────────────┘
                    │
                    ▼
            /test-plan-publish (commit & push updates)
```

## Prerequisites

### Required for All Users
- [Claude Code](https://claude.ai/code) installed
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Git installed
- Python 3.10 or higher

### Required for Specific Features
- **Jira integration**: [Atlassian MCP server](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/) configured (for `/test-plan-create`)
- **GitHub publishing**: [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (for `/test-plan-publish` and `/test-plan-resolve-feedback`)
- **Test implementation**: Local or cloned target repositories (for `/test-plan-case-implement`)

## Repository Structure

```
.claude-plugin/
└── plugin.json             # Plugin metadata (v1.0.0)

skills/
├── test-plan-create/
│   ├── SKILL.md
│   └── test-plan-template.md
├── test-plan-analyze-endpoints/
│   └── SKILL.md
├── test-plan-analyze-risks/
│   └── SKILL.md
├── test-plan-analyze-infra/
│   └── SKILL.md
├── test-plan-analyze-placement/
│   └── SKILL.md
├── test-plan-merge/
│   └── SKILL.md
├── test-plan-resolve-gaps/
│   └── SKILL.md
├── test-plan-review/
│   └── SKILL.md
├── test-plan-create-cases/
│   ├── SKILL.md
│   └── test-case-template.md
├── test-plan-update/
│   └── SKILL.md
├── test-plan-publish/
│   └── SKILL.md
├── test-plan-resolve-feedback/
│   └── SKILL.md
├── test-plan-case-implement/
│   └── SKILL.md            # Main orchestration skill
├── test-plan-generate-test-file/
│   └── SKILL.md            # Test file generation sub-agent
├── test-plan-ui-verify/
│   ├── README.md
│   └── SKILL.md
├── test-plan-score/
│   └── SKILL.md
└── _common/                # Shared scripts (symlinked)

scripts/
├── frontmatter.py          # YAML frontmatter validation and manipulation
├── repo.py                 # Repository discovery, cloning, validation
├── tc_regeneration.py      # Test case regeneration mode detection
├── preflight.py            # Unified preflight checks (validation + detection + odh-test-context)
├── validate_feature_dir.py # Feature directory structure validation
├── detect_components.py    # Component detection and repository mapping
├── filter_test_cases.py    # Filter test cases by automation status
├── map_test_files.py       # Map test cases to test files (strategy pattern)
├── list_test_functions.py  # Extract test functions from Python files (AST)
├── load_pattern_guides.py  # Load CLAUDE.md and testing pattern guides
├── parse_test_score.py     # Parse test quality score assessments
├── update_tc_frontmatter.py # Bulk update TC frontmatter fields
└── utils/                  # Shared utilities
    ├── schemas.py          # Schema validation (test-plan, test-case, test-gaps, review)
    ├── frontmatter_utils.py # Frontmatter read/write operations
    ├── repo_utils.py       # Repository discovery and test context loading
    ├── component_map.py    # Component to repository mapping
    ├── repo_discovery.py   # Extract repo indicators from test plans
    ├── tc_parser.py        # Test case file parsing (extended with category/title extraction)
    ├── text_utils.py       # Text transformation utilities (snake_case conversion)
    └── test_analyzer.py    # Common setup requirements identification
```

## Development

### Prerequisites

Install the package in development mode with dev dependencies:

```bash
uv sync --extra dev
```

This installs:
- The `test-plan` package in editable mode (changes are immediately available)
- `pyyaml` - YAML frontmatter parsing
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting

### Running Tests

Run all tests:
```bash
uv run pytest tests/ -v
```

Run a specific test file:
```bash
uv run pytest tests/test_schema_validation.py -v
```

Run tests with coverage:
```bash
uv run pytest tests/ -v --cov=scripts --cov-report=term-missing
```

Run a specific test:
```bash
uv run pytest tests/test_schema_validation.py::TestPlanSchemaValidation::test_field_validation -v
```

### Test Structure

```
tests/
├── constants.py                      # Shared test data constants
├── unit/                             # Unit tests (fast, isolated)
│   ├── test_schema_validation.py     # Schema validation (test-plan, test-case, test-gaps)
│   ├── test_frontmatter_operations.py # Read, write, update operations
│   ├── test_frontmatter_cli_unit.py  # CLI interface tests
│   ├── test_detect_components.py     # Component detection and repo mapping
│   ├── test_filter_test_cases.py     # Test case filtering by status
│   ├── test_map_test_files.py        # File mapping with strategy pattern
│   ├── test_list_test_functions.py   # AST-based function extraction
│   ├── test_load_pattern_guides.py   # Pattern guide loading
│   ├── test_parse_test_score.py      # Score file parsing
│   ├── test_update_tc_frontmatter.py # Bulk frontmatter updates
│   ├── test_validate_feature_dir.py  # Directory validation
│   ├── test_text_utils.py            # Text sanitization utilities
│   ├── test_tc_parser_utils.py       # TC category/title extraction
│   ├── test_repo_cli.py              # Repository CLI tests
│   ├── test_repo_discovery.py        # Repository indicator extraction
│   ├── test_repo_utils.py            # Repository utility functions
│   ├── test_analyzer.py              # Common setup identification
│   └── test_ui_verify_helpers.py     # UI test helpers
└── integration/                      # Integration tests (subprocess, file I/O)
    ├── test_artifact_utils_validation.py # Review schema validation
    ├── test_filter_for_revision.py   # Revision filter (subprocess)
    ├── test_preserve_review_state.py # State persistence
    └── test_tc_parser.py             # TC file parsing integration tests
```
