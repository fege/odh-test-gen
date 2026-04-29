# Test Plan

End-to-end test planning workflow for RHOAI: generate test plans from strategies, create test cases, implement executable automation code, verify UI tests against live clusters via Playwright, publish to GitHub with PR creation, resolve review feedback, and score quality with automated rubrics using parallel sub-agent analysis.

## Skills

### User-invocable

| Skill | Description |
|-------|-------------|
| `/test-plan.create` | Generate a test plan from a strategy (RHAISTRAT or RHOAIENG), with optional ADR |
| `/test-plan.create-cases` | Generate individual test case files from an existing test plan |
| `/test-plan.update` | Update test plan with new docs (ADR, API specs), re-analyze, bump version |
| `/test-plan.case-implement` | Generate executable test automation code from TC specifications with intelligent placement |
| `/test-plan.ui-verify` | Verify UI test cases from a PR against a live ODH/RHOAI cluster via Playwright; supports upgrade testing workflow — see [README](.claude/skills/test-plan.ui-verify/README.md) |
| `/test-plan.publish` | Publish test plan artifacts to GitHub — branch, commit, and open a PR |
| `/test-plan.resolve-feedback` | Assess PR review comments, let the user decide what to apply, and push updates |
| `/test-plan.score` | Score an existing test plan using quality rubric (without auto-revision) |

### Sub-agents (forked, non-user-invocable)

| Skill | Description |
|-------|-------------|
| `test-plan.analyze.endpoints` | Extract feature scope, test objectives, and API endpoints/methods |
| `test-plan.analyze.risks` | Determine test levels, types, priorities, and risks |
| `test-plan.analyze.infra` | Identify environment config, test data, infrastructure requirements |
| `test-plan.merge` | Intelligently merge new analyzer findings into existing test plan |
| `test-plan.resolve-gaps` | Cross-reference gaps with new findings to determine what's resolved |
| `test-plan.analyze.placement` | Analyze test cases and recommend placement (component repo vs downstream) |
| `test-plan.review` | Review test plan for completeness, consistency, and quality |
| `test-plan.create.test-function` | Generate test function code from TC specification matching repo conventions |
| `test-plan.score.test-function` | Score generated test function code using 5-criteria quality rubric |

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
cd ~/.claude/plugins/cache/opendatahub-skills/test-plan/<version>
uv pip install -e ".[dev]"
```

Use skills:
```bash
# Will prompt for artifact location (default: ~/Code/collection-tests)
/test-plan.create RHAISTRAT-400

# Auto-uses location from /test-plan.create
/test-plan.create-cases

# Will prompt for publish target (default: fege/collection-tests)
/test-plan.publish
```

### Option 2: Manual Clone (For Contributors)

Clone the repository directly:

```bash
git clone https://github.com/fege/test-plan ~/Code/test-plan
cd ~/Code/test-plan
uv pip install -e ".[dev]"
```

Skills are available from `.claude/skills/` directory.

**Note**: Skills use symlinks for shared utilities (`test-plan-common/scripts → ../../../scripts`). Both installation methods clone the full repository, so symlinks resolve correctly.

Each skill includes an `argument-hint` field in its frontmatter for autocomplete guidance when typing slash commands.

## Artifact Location

**Important**: Test plan artifacts are kept separate from the skill repository to maintain clean boundaries between code and data.

### Default Behavior

When you run `/test-plan.create`, it asks where to save artifacts:
```
Where should test plan artifacts be created?

Provide a directory path, or press Enter for: ~/Code/collection-tests
```

- **QE Teams**: Typically work in their own test plans repository (e.g., `~/Code/opendatahub-test-plans/`)
- **Contributors**: Use default `~/Code/collection-tests` to keep artifacts out of the skill repo
- **Save Preference**: Optionally save your choice to `.claude/settings.json` for future runs

### Session Context

`/test-plan.create-cases` automatically uses the same location as `/test-plan.create` when run in the same session (no prompt needed).

### Publishing

`/test-plan.publish` always publishes to an external repository:
- Default: `fege/collection-tests`
- Prevents accidental publishing to the skill repository
- Automatically detects and switches to the correct directory

### Contributor Override

Contributors testing skills can use `--output-dir` to force creation in the current directory:
```bash
/test-plan.create RHAISTRAT-400 --output-dir .
```

**Note**: The skill repository blocks artifact creation by default to prevent mixing code and test plan data.

## Usage

### Basic Workflow

```bash
# 1. Generate a test plan from a Jira strategy
#    Will ask: Where to save artifacts? [~/Code/collection-tests]
/test-plan.create RHAISTRAT-400

# 2. Generate test cases (auto-uses location from step 1)
/test-plan.create-cases

# 3. Publish to GitHub
#    Will ask: Where to publish? [fege/collection-tests]
/test-plan.publish mcp_catalog
```

### Advanced Options

```bash
# Generate test plan with ADR for extra technical depth
/test-plan.create RHAISTRAT-400 /path/to/adr.pdf

# Generate test cases from a GitHub PR (for /test-plan.resolve-feedback workflow)
/test-plan.create-cases https://github.com/fege/collection-tests/pull/5

# Generate test cases for a specific local directory
/test-plan.create-cases ~/Code/collection-tests/mcp_catalog

# Publish with specific reviewers
/test-plan.publish mcp_catalog --reviewers alice,bob

# Publish to a specific repository
/test-plan.publish mcp_catalog --repo opendatahub-io/test-plans

# Resolve PR review feedback
/test-plan.resolve-feedback https://github.com/fege/collection-tests/pull/42

# Update test plan with new documentation
/test-plan.update ~/Code/collection-tests/mcp_catalog adr.pdf api-spec.md

# Update test plan from GitHub PR with new docs
/test-plan.update https://github.com/fege/collection-tests/pull/42 design-doc.md

# Generate executable test code from test cases
/test-plan.case-implement mcp_catalog

# Generate code for specific test cases only
/test-plan.case-implement mcp_catalog --test-cases TC-API-001,TC-API-002

# Score a test plan without triggering auto-revision
/test-plan.score mcp_catalog
```

### Contributor Workflow

```bash
# Force creation in current directory (bypasses skill repo validation)
/test-plan.create RHAISTRAT-400 --output-dir .

# Force test case creation in current directory
/test-plan.create-cases mcp_catalog --output-dir .
```

## Pipeline

```
/test-plan.create RHAISTRAT-400
        │
        ├── test-plan.analyze.endpoints  ─┐
        ├── test-plan.analyze.risks      ─┤  (parallel)
        └── test-plan.analyze.infra      ─┘
                    │
                    ▼
            TestPlan.md + TestPlanGaps.md
                    │
                    ▼
            Gap resolution (HITL)
                    │
                    ▼
            test-plan.review (auto-revision, scoring)
                    │
                    ▼
        /test-plan.create-cases (optional auto-run)
                    │
                    ▼
            TC-*.md + INDEX.md
                    │
                    ├─────────────────────┐
                    │                     │
                    ▼                     ▼
        /test-plan.publish    /test-plan.case-implement
                    │                     │
                    │                     ├── test-plan.analyze.placement
                    │                     ├── test-plan.create.test-function (per TC)
                    │                     └── test-plan.score.test-function (per TC)
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
        /test-plan.resolve-feedback          /test-plan.update (new docs)
        (after PR reviews)                    │
                    │                         ├── re-run analyzers
                    │                         ├── update TestPlan.md
                    │                         ├── test-plan.review
                    │                         └── optionally regenerate test cases
                    │                         │
                    ▼                         ▼
            Updated artifacts ◄───────────────┘
                    │
                    ▼
            /test-plan.publish (commit & push updates)
```

## Prerequisites

### Required for All Users
- [Claude Code](https://claude.ai/code) installed
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Git installed
- Python 3.10 or higher

### Required for Specific Features
- **Jira integration**: [Atlassian MCP server](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/) configured (for `/test-plan.create`)
- **GitHub publishing**: [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (for `/test-plan.publish` and `/test-plan.resolve-feedback`)
- **Test implementation**: Local or cloned target repositories (for `/test-plan.case-implement`)

## Repository Structure

```
.claude/skills/
├── test-plan.create/
│   ├── SKILL.md
│   └── test-plan-template.md
├── test-plan.analyze.endpoints/
│   └── SKILL.md
├── test-plan.analyze.risks/
│   └── SKILL.md
├── test-plan.analyze.infra/
│   └── SKILL.md
├── test-plan.merge/
│   └── SKILL.md
├── test-plan.resolve-gaps/
│   └── SKILL.md
├── test-plan.review/
│   └── SKILL.md
├── test-plan.create-cases/
│   ├── SKILL.md
│   └── test-case-template.md
├── test-plan.update/
│   └── SKILL.md
├── test-plan.publish/
│   └── SKILL.md
├── test-plan.resolve-feedback/
│   └── SKILL.md
└── test-plan.ui-verify/
    ├── README.md
    └── SKILL.md

scripts/
├── frontmatter.py          # YAML frontmatter validation and manipulation
├── repo.py                 # Repository discovery, cloning, validation, and feature location
├── tc_regeneration.py      # Test case regeneration mode detection
└── utils/                  # Shared utilities (schemas, repo utils, frontmatter utils)
```

## Development

### Prerequisites

Install the package in development mode with dev dependencies:

```bash
uv pip install -e ".[dev]"
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
│   └── test_frontmatter_cli_unit.py  # CLI interface tests
└── integration/                      # Integration tests (subprocess, file I/O)
    ├── test_artifact_utils_validation.py # Review schema validation
    ├── test_filter_for_revision.py   # Revision filter (subprocess)
    └── test_preserve_review_state.py # State persistence
```
