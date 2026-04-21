# Test Case Implementation Generator - Reference Documentation

This document provides reference information for the `/test-plan.case-implement` skill.

For execution instructions, see [SKILL.md](SKILL.md).

---

## Sub-Agents (Forked, Non-User-Invocable)

This skill uses the following forked sub-agents:

### test-plan.analyze.placement
- **When**: Step 2 (placement decision for each TC)
- **Input**: Feature dir, code repo info, repo capabilities (readiness, has_tests)
- **Output**: Per-TC placement recommendations (same_repo/downstream/both) with scores and reasoning
- **Purpose**: Analyze TC characteristics and recommend optimal placement using refined scoring algorithm
- **User interaction**: Presents recommendations, allows per-TC override
- **user-invocable**: false

### test-plan.create.test-function
- **When**: Step 5.3 (test code generation from TC specs)
- **Input**: TC file, function name, framework, conventions, pattern guide, repo instructions, common setup, target repo, placement
- **Output**: Test function code (framework-specific: pytest/Go/TypeScript/etc.)
- **Purpose**: Generate test function from TC specification matching repository conventions
- **Parallelization**: Invoked once per TC, all run in parallel for speed
- **user-invocable**: false

### test-plan.score.test-function
- **When**: Step 5.6 (quality assessment after test generation)
- **Input**: Generated test code, TC file, conventions file, framework, output file path
- **Output**: Quality assessment written to file with score (0-10), verdict, issues, revision feedback
- **Purpose**: Score test quality using 5-criteria rubric (coverage, assertions, conventions, test data, code quality)
- **Triggers auto-revision**: If score 4-6, regenerates test with feedback from score file
- **user-invocable**: false

---

## Utility Scripts

This skill uses the following utility scripts:

### scripts/utils/repo_utils.py
- `find_known_repo(repo_type)` - Locate known repos ('odh-test-context', 'tiger-team'), returns (path, clone_url)
- `find_target_repo(repo_name)` - Find target code repo in common locations
- `find_repo_in_common_locations(repo_name)` - Search common locations for a repository
- `clone_repo(repo_url, target_path)` - Clone Git repository from GitHub
- `map_components_to_repos(components, odh_path)` - Map component names to GitHub repos
- `load_repo_test_context(repo_name, odh_path)` - Load test context JSON from odh-test-context
- `extract_conventions_from_context(test_context)` - Extract conventions from odh-test-context
- `get_framework(test_context)` - Get test framework from odh-test-context data

### scripts/utils/schemas.py
- `SCHEMAS` - Schema definitions for all artifact types
- `validate(data, schema_type)` - Validate frontmatter against schema
- `apply_defaults(data, schema_type)` - Apply default values
- `detect_schema_type(path)` - Detect schema from filename
- `get_schema_yaml(schema_type)` - Get schema as YAML string
- `ValidationError` - Exception for validation failures

### scripts/utils/frontmatter_utils.py
- `read_frontmatter(file_path)` - Read YAML frontmatter from file, returns (dict, body)
- `read_frontmatter_validated(file_path, schema_type)` - Read and validate frontmatter
- `write_frontmatter(file_path, data, schema_type)` - Write validated frontmatter
- `update_frontmatter(file_path, updates, schema_type)` - Update specific fields

### scripts/utils/tc_parser.py
- `parse_tc_file(tc_file, read_frontmatter_func)` - Parse TC file into structured data (extracts Objective, Preconditions, Test Steps, Expected Results)

### scripts/utils/repo_discovery.py
- `extract_repo_indicators(testplan_path, tc_files)` - Extract components and endpoints from TestPlan.md using hardcoded keywords

### scripts/utils/test_analyzer.py
- `identify_common_setup_requirements(test_cases)` - Identify preconditions used by 2+ TCs (framework-agnostic)

### scripts/utils/component_map.py
- `COMPONENT_REPO_MAP` - Authoritative component → repo mapping from odh-build-metadata

---

## Dependencies

### Required
- **Python 3.8+** - For test code generation and validation
- **uv** - For running frontmatter scripts
- **git** - For cloning repositories
- **gh CLI** - For fetching artifacts from GitHub branches (if feature source is remote)

### Recommended (High Value)
- **odh-test-context** repository at `~/Code/odh-test-context` (or custom path)
  - Provides pre-analyzed test context for ~162 opendatahub-io repos
  - Includes: framework detection, conventions, linting, container recipes, agent_readiness
  - **Significantly improves** placement decisions and test quality
  - Source: https://github.com/opendatahub-io/odh-test-context
  - If missing: Skill offers to clone or proceed with manual discovery

- **Red-Hat-Quality-Tiger-Team** repository at `~/Code/Red-Hat-Quality-Tiger-Team` (or custom path)
  - Provides test pattern guides (go-tests.md, typescript-unit-tests.md, cypress-tests.md, testing-standards.md)
  - Guides provide code patterns, examples, and anti-patterns for test generation
  - Source: https://github.com/RedHatQE/Red-Hat-Quality-Tiger-Team
  - If missing: Skill offers to clone or auto-generate via Tiger Team's test-rules-generator

### Optional
- **podman** or **docker** - For container validation of generated tests (if odh-test-context provides container_recipe)
- **pytest** - If target repo uses pytest framework

---

## How Dependencies Work Together

### For Placement Decisions (Step 2):
```
odh-test-context                 test-plan.analyze.placement
(repo capabilities)         →    (scoring algorithm)
     ↓                                  ↓
"Repo has agent_readiness=high,   Analyzes TC characteristics,
 tests/ dir exists, pytest"       scores placement options
     ↓                                  ↓
     └──────────────────┬───────────────┘
                        │
            User confirms placement
            (same_repo / downstream / both)
```

### For Test Code Generation (Step 5.3):
```
Tiger Team pattern guides     odh-test-context         test-plan.create.test-function
(code patterns, examples)  +  (basic conventions)  →   (sub-agent)
          ↓                           ↓                       ↓
   "Use Ginkgo BeforeSuite,    "Framework: pytest,      Generated test code
    mock with gofakeit,         file pattern: test_*.py" matching repo style
    assert with Gomega"         
```

**Component Roles**:
1. **odh-test-context** - Repo structure data (framework, dirs, agent_readiness) → Used for placement scoring
2. **Tiger Team pattern guides** - Code style guides (how to write tests) → Used by test generator sub-agent
3. **test-plan.analyze.placement** - Placement algorithm (where tests go) → Makes recommendations, user confirms

---

## What this skill does NOT do

- Does NOT generate test plan or test case specifications — use `/test-plan.create` and `/test-plan.create-cases` for that
- Does NOT execute tests or verify they pass — generated tests must be reviewed and run manually
- Does NOT commit tests to target repository — user must review, run, and commit manually
- Does NOT guarantee 100% correct test code — always requires manual review and enhancement
- Does NOT resolve test failures or debug test issues — troubleshooting is manual
- Does NOT update test plan coverage metrics — use `/coverage-assessment` for that
- Does NOT create fixtures or test data files automatically — only suggests them in summary report

**Supported test frameworks**: pytest, unittest, Playwright (Python); Ginkgo/Gomega, go-testing (Go); Jest, Cypress (TypeScript/JavaScript)
