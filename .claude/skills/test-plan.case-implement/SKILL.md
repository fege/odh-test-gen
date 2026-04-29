---
name: test-plan.case-implement
description: Generate executable test automation code from test case specifications
argument-hint: "[FEATURE_SOURCE] [--test-cases TC-ID,TC-ID] [--target-repo PATH]"
user-invocable: true
model: opus
allowedTools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Skill
  - AskUserQuestion
---

# Test Case Implementation Generator

Generate executable test automation code (pytest, etc.) from TC-*.md test case specification files, with intelligent auto-placement in component repos or downstream E2E repo.

## Usage

```
/test-plan.case-implement [FEATURE_SOURCE] [--test-cases TC-API-001,TC-API-002] [--target-repo ~/Code/opendatahub-tests]
```

Examples:
- `/test-plan.case-implement` (auto-detects from prior `/test-plan.publish` or `/test-plan.create-cases` run)
- `/test-plan.case-implement features/notebooks/RHAISTRAT-400-notebook-spawning`
- `/test-plan.case-implement test-plan/RHAISTRAT-400` (GitHub branch)
- `/test-plan.case-implement --test-cases TC-API-001,TC-API-002` (selective)
- `/test-plan.case-implement features/notebooks/RHAISTRAT-400 --target-repo ~/Code/opendatahub-tests`

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **First argument** (optional): Feature source - local directory or GitHub branch containing test case artifacts
   - Local path: `features/notebooks/RHAISTRAT-400-notebook-spawning`
   - GitHub branch: `https://github.com/org/repo/tree/test-plan/RHAISTRAT-400` or `test-plan/RHAISTRAT-400`
2. **`--test-cases`** (optional): Comma-separated list of test case IDs to implement (e.g., `TC-API-001,TC-API-002,TC-E2E-001`)
3. **`--target-repo`** (optional): Override auto-detected target repository path or URL

### Interactive fallback
If no feature source argument is provided, ask the user via AskUserQuestion:
> **Where is the test plan with test cases to implement?**
>
> You can provide:
> - Local directory path (e.g., `~/Code/collection-tests/evalhub_metrics`)
> - GitHub branch URL (e.g., `https://github.com/org/repo/tree/test-plan/RHAISTRAT-1507`)
> - GitHub PR URL (e.g., `https://github.com/fege/collection-tests/pull/4`)

## Process

### Step 0: Pre-flight Checks


#### 0.1 Fetch feature artifacts

If feature source is a GitHub branch:
1. Parse branch name from URL or short form (e.g., `test-plan/RHAISTRAT-400`)
2. Parse owner/repo from URL (e.g., `fege/test-plan`)
3. **Check if repo exists locally**:
   ```bash
   repo_path=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py find "<repo_name>")
   ```
   - If found (exit code 0, prints path):
     - Check if already on branch, update to latest:
       ```bash
       cd "$repo_path"
       current_branch=$(git branch --show-current)

       if [ "$current_branch" = "<branch_name>" ]; then
           # Already on the branch, just pull latest
           git pull origin <branch_name>
       else
           # Need to switch branches
           git fetch origin
           git checkout <branch_name> 2>/dev/null || git checkout -b <branch_name> origin/<branch_name>
           git pull origin <branch_name>
       fi
       ```
     - Set `feature_dir` to `$repo_path/<feature_name>`
     - Log: "✓ Using local clone: $repo_path (updated)"
   - If NOT found (exit code 1, empty output):
     - Clone the repo:
       ```bash
       clone_path=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py clone "<repo_url>" "~/Code/<repo_name>")
       ```
     - Checkout branch:
       ```bash
       cd "$clone_path"
       git checkout <branch_name>
       ```
     - Set `feature_dir` to `$clone_path/<feature_name>`
     - Log: "✓ Cloned to $clone_path"

If feature source is a local path:
1. Verify path exists and is a directory
2. Set `feature_dir` to the provided path

#### 0.2 Validate feature directory structure

1. Check `<feature_dir>/TestPlan.md` exists
2. Check `<feature_dir>/test_cases/` directory exists
3. Check `<feature_dir>/test_cases/INDEX.md` exists
4. Check at least one `TC-*.md` file exists in `test_cases/`
5. Read `TestPlan.md` frontmatter to extract: `source_key`, `feature`, `version`, `components`:
   ```bash
   frontmatter_json=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py read <feature_dir>/TestPlan.md)
   components_from_fm=$(echo "$frontmatter_json" | jq -r '.components // [] | join(",")')
   ```
   - Store `components_from_fm` (comma-separated list, e.g., `"AI Hub,Model Serving"`)
   - If empty or `[]`, set to empty string

If any check fails, inform the user and stop.

#### 0.3 Locate odh-test-context repository

Find odh-test-context repository:
```bash
odh_result=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py find-known odh-test-context)
odh_path=$(echo "$odh_result" | jq -r '.path')
odh_url=$(echo "$odh_result" | jq -r '.url')
```

This checks common locations:
- `~/Code/odh-test-context`
- `~/odh-test-context`
- `~/workspace/odh-test-context`
- `../odh-test-context` (relative to current repo)

If NOT found (exit code 1, `odh_path` is "null"), prompt user via AskUserQuestion:
> odh-test-context repository not found. This repository provides validated test conventions and placement guidance for ~162 opendatahub-io repos.
>
> Options:
> 1. **Specify path** - Provide path to existing local clone
> 2. **Clone from GitHub** - Clone opendatahub-io/odh-test-context to ~/Code/
> 3. **Proceed without it** - Use manual discovery (slower, less accurate)
>
> Choice [1/2/3]:

Returns:
- `odh_test_context_path` (str or None if user declined)

#### 0.4 Identify code repository

Gather component indicators from multiple sources (merge all):

**Source 1: Frontmatter components** (from Jira ticket, highest authority):
- Use `components_from_fm` extracted in Step 0.2
- Split comma-separated list into array: `["AI Hub", "Model Serving"]`

**Source 2: Content extraction**:
- Use `scripts/utils/repo_discovery.py::extract_repo_indicators(testplan_path, tc_files)` to extract:
  1. Read endpoints from `TestPlan.md` Section 4
  2. Extract components from `TestPlan.md` Section 1.2 (Scope) 
  3. Sample 3 TC-*.md files and extract component mentions from preconditions
- Uses hardcoded component keywords for common opendatahub-io repos (dashboard, notebooks, model-registry, pipelines, kserve, modelmesh, distributed-workloads, trustyai, etc.)

**Merge**:
- Combine frontmatter components + content-discovered components
- Remove duplicates
- Frontmatter components have **higher weight** in repo mapping (Step 0.5)

Returns: `{'components': [...], 'endpoints': [...], 'frontmatter_components': [...]}`

#### 0.5 Map components to repositories and confirm with user

Use `scripts/utils/component_map.py::get_repo_for_component(component)` to map detected components to repos:

1. For each component from Step 0.4, look it up using `get_repo_for_component(component)` (handles case-insensitive matching)
2. Collect matched repos: `{component: repo, source: 'frontmatter'|'content'}`
3. Get unique repos from matched values
4. **Prioritize repos matched by frontmatter components** when presenting options

**Always ask user for confirmation:**

If **exactly 1 unique repo** matched:
1. Present via AskUserQuestion:
   > ✓ Auto-detected code repository: **{repo}**
   > 
   > Based on components: {component_list} {show (from Jira) for frontmatter components}
   > 
   > Proceed with this repository? [yes/specify-different]

2. If **yes**: Set `code_repo = repo`, proceed to Step 0.6
3. If **specify-different**: Ask for repo name (e.g., `opendatahub-io/notebooks`)

If **multiple unique repos** matched:
1. **Sort by priority**: repos matched by frontmatter components first
2. Present via AskUserQuestion:
   > Multiple repositories detected from components:
   > 1. **{repo1}** (from Jira: {fm_components}, from content: {content_components})
   > 2. **{repo2}** (from content: {components})
   > 
   > Which is the primary target? [1/2/specify-different]

2. Set `code_repo` based on choice

If **no repos** matched:
1. Show detected components that didn't match
2. Ask via AskUserQuestion:
   > No repository match found for components: {components}
   > 
   > Please specify the GitHub repository (e.g., opendatahub-io/repo-name):

3. Set `code_repo` from user input

Store: `code_repo` (e.g., `opendatahub-io/odh-dashboard`)

#### 0.6 Locate code repository locally

1. Check common locations for the code repository:
   ```bash
   code_repo_path=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py find-target "<code_repo>")
   ```
   This checks:
   - `~/Code/<repo_name>`
   - `~/Code/<org>-<repo_name>`
   - `~/<repo_name>`
   - `~/workspace/<repo_name>`

2. If found (exit code 0, prints path):
   - Set `code_repo_path`
   - Proceed to Step 1

3. If NOT found (exit code 1, empty output):
   - Ask user via AskUserQuestion: `Clone <code_repo>? [yes/no/specify-path]`
   - If **yes**: Clone it:
     ```bash
     code_repo_path=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py clone "<repo_url>" "~/Code/<repo_name>")
     ```
   - If **specify-path**: Ask for manual path, validate it exists
   - If **no**: Stop (cannot proceed without code repo)

Returns: `code_repo_path` (str or None)

### Step 1: Load Testing Context

#### 1.0 Load odh-test-context for code repository

Use `scripts/utils/repo_utils.py::load_repo_test_context(repo_name, odh_test_context_path)`:

If odh-test-context is available:
1. Checks for `<odh_test_context_path>/tests/<repo_name>.json`
2. If found:
   - Reads and parses JSON
   - Returns context dict with: framework, directories, commands, conventions, linting, agent_readiness, container_recipe
3. If NOT found:
   - Returns None

Script saves context to `<feature_dir>/test_implementation_context.json` if found.

Returns:
- `test_context` (dict or None)
- `use_odh_context` (bool)

#### 1.0b Load downstream E2E repository context

Use `scripts/utils/repo_utils.py::load_repo_test_context('opendatahub-tests', odh_test_context_path)`:

Returns:
- `downstream_context` (dict with framework, conventions, markers, agent_readiness)
- Falls back to defaults if not found: pytest, basic markers, agent_readiness=medium

#### 1.1 Detect test framework

Use `scripts/utils/repo_utils.py::get_framework(test_context)`:

If `test_context` exists: returns `test_context['testing']['framework']`

If NOT (manual detection):
1. Checks for pytest indicators (pytest.ini, pyproject.toml, conftest.py)
2. Checks for unittest indicators (import unittest in .py files)
3. Checks for Playwright indicators (playwright.config.js/ts)
4. Checks for Robot Framework indicators (*.robot files)
5. Checks for Go testing indicators (*_test.go files, Ginkgo imports)
6. Checks for Jest indicators (jest.config.js, .spec.ts files, describe/it blocks)
7. Checks for Cypress indicators (.cy.ts/.cy.js files, cy. commands)
8. If unknown: asks user via AskUserQuestion

Returns: `framework` (str: pytest, unittest, playwright, robot, ginkgo, go-testing, jest, cypress)

#### 1.2 Load test conventions

If `use_odh_context == True`:
1. Use `scripts/utils/repo_utils.py::extract_conventions_from_context(test_context)` to extract:
   - File patterns, function patterns, import style, markers
   - Linting tools and commands
   - Testing directories and execution commands
2. Generate conventions summary markdown
3. Write to `<feature_dir>/test_implementation_conventions.md`

If `use_odh_context == False` (no odh-test-context available):
1. Conventions will be minimal (framework only, from Step 1.1)
2. Test generation will rely more heavily on Tiger Team pattern guides (Step 1.2b)
3. Generated tests may be less optimized for the specific repo
4. **For new components**: Consider contributing to odh-test-context for future use:
   - Repository: https://github.com/opendatahub-io/odh-test-context
   - Add JSON file: `tests/<repo_name>.json` with discovered framework, test directories, conventions, linting tools
   - See existing files in `tests/` directory as examples
   - Improves test quality for all future test generation on this component

Store: `conventions` (dict or markdown content)

#### 1.2b Load or generate testing pattern guides (REQUIRED before test generation)

**Purpose**: Load testing pattern guides (.md files) that describe HOW to write tests matching repo style. These guides provide code patterns, examples, and anti-patterns for the test-function generation sub-agent. They do NOT define test placement.

**CRITICAL**: Do NOT proceed to test generation without attempting to load or generate pattern guides. This step MUST be executed.

---

**Step 0: Check for repository-specific instructions (CHECK FIRST)**

Check for conventional agentic instruction files in the code repository (CLAUDE.md, AGENTS.md, CONSTITUTION.md):

```bash
cd <code_repo_path>
# Check both .claude/ and root for each file type
repo_files=()
for filename in CLAUDE.md AGENTS.md CONSTITUTION.md; do
    if [ -f ".claude/$filename" ]; then
        repo_files+=(".claude/$filename")
    elif [ -f "$filename" ]; then
        repo_files+=("$filename")
    fi
done

# Print found files (one per line)
printf '%s\n' "${repo_files[@]}"
```

If any files found:
1. Read all found files
2. Combine content into a single context document with clear section headers:
   ```markdown
   # Repository-Specific Instructions

   ## From CLAUDE.md
   {content if found}

   ## From AGENTS.md
   {content if found}

   ## From CONSTITUTION.md
   {content if found}
   ```
3. Write to `<feature_dir>/repo_instructions.md`
4. Store path as `repo_instructions_file`
5. Log: "✓ Found repo instructions: {comma-separated list of files}"

If NO files found:
- Set `repo_instructions_file = None`
- Continue (not required, but helpful when available)

**What these files typically contain:**
- **CLAUDE.md**: Codebase context, conventions, testing guidance, code style
- **AGENTS.md**: Agent-specific instructions, workflows, tool usage patterns
- **CONSTITUTION.md**: Hard constraints, principles, rules that must not be violated

**IMPORTANT**: These files provide high-authority repo-specific guidance that supplements odh-test-context and pattern guides.

---

**Step 1: Check if component repo already has pattern guides**

Look for existing guides in code repo (may have been generated previously by Tiger Team):
```bash
cd <code_repo_path>
# Check .claude/rules/ directory (Tiger Team output location)
if [ -d ".claude/rules" ]; then
    ls .claude/rules/*-tests.md testing-standards.md 2>/dev/null
fi
```

Common pattern files:
- `go-tests.md` - Go testing patterns (Ginkgo/Gomega, testify, mocks)
- `pytest-tests.md` - Python pytest patterns (fixtures, markers, parametrize)
- `typescript-unit-tests.md` - TypeScript/Jest/React Testing Library patterns
- `cypress-tests.md` - Cypress E2E patterns
- `testing-standards.md` - Cross-cutting testing standards

If found:
1. Read the relevant guide for our framework (e.g., `pytest-tests.md` if framework=pytest)
2. Store as `testing_pattern_guide = <guide_content>`
3. Log: "✓ Found existing testing pattern guide: <guide_file>"
4. **Skip Step 2 (do NOT generate)** - Proceed to Step 1.3

**IMPORTANT**: Pattern guide is now loaded and ready for test generation in Step 5.3

---

**Step 2: If NOT found in Step 1, auto-generate via Tiger Team (MANDATORY)**

**CRITICAL**: This step MUST be executed if Step 1 found NO pattern guides. Do NOT skip to test generation without pattern guides.

If no pattern guides exist in component repo:

1. Locate Tiger Team repository:
   ```bash
   tiger_result=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py find-known tiger-team)
   tiger_path=$(echo "$tiger_result" | jq -r '.path')
   tiger_url=$(echo "$tiger_result" | jq -r '.url')
   ```

2. **If Tiger Team found locally** (exit code 0, `tiger_path` is not "null"):
   - **Auto-generate** pattern guides (no user prompt):
     ```bash
     /test-rules-generator <code_repo_path>
     ```
   - Tiger Team creates guides in `<code_repo_path>/.claude/rules/`:
     - `pytest-tests.md` (if Python/pytest)
     - `go-tests.md` (if Go)
     - `typescript-unit-tests.md` (if TypeScript/Jest)
     - `testing-standards.md` (cross-cutting)
   - Read the guide for our framework
   - Store as `testing_pattern_guide`
   - Log: "✓ Auto-generated pattern guides using Tiger Team"

3. **If Tiger Team NOT found** (returns None):
   - Ask via AskUserQuestion:
     > Tiger Team not found locally. Clone and generate test pattern guides? [yes/no]
   
   - If **yes**:
     - Clone: `git clone https://github.com/RedHatQE/Red-Hat-Quality-Tiger-Team ~/Code/Red-Hat-Quality-Tiger-Team`
     - Generate as above
   
   - If **no**:
     - Set `testing_pattern_guide = None`
     - Log: "⚠ Skipped pattern guide generation. Using basic conventions only."

Store: `testing_pattern_guide` (str or None)

**After Step 1.2b completes**, you should have EITHER:
- ✅ Pattern guide loaded from component repo, OR
- ✅ Pattern guide generated by Tiger Team, OR
- ⚠️ No pattern guide (user declined - tests will use basic conventions only)

**Do NOT proceed to Step 2 (placement analysis) without completing Step 1.2b.**

---

**How pattern guides are used**:
- Passed to `test-plan.create.test-function` sub-agent in Step 5.3
- Sub-agent reads the guide to learn repo-specific test patterns
- Generates tests matching: naming, structure, mocking patterns, assertion styles, setup/teardown
- **NOT used for placement** (placement = odh-test-context + Step 2.2 scoring)

#### 1.3 Offer container validation

If `use_odh_context == True` AND `test_context` contains `container_recipe`:
1. Show user the container validation option via AskUserQuestion:
   > Container validation is available using odh-test-context.
   > - Base image: <container_recipe.base_image>
   > - Can validate linting and test execution in isolated environment
   >
   > Validate generated tests in container after creation? [yes/no]

2. If **yes**: Set `validate_in_container = True` and store `validation_recipe = test_context['container_recipe']`
3. If **no**: Set `validate_in_container = False`

If container recipe NOT available:
1. Set `validate_in_container = False`

### Step 2: Per-TC Placement Analysis

Extract repository capabilities from context (from Step 1):
- `code_repo_readiness` = `test_context.get('agent_readiness', 'unknown')`
- `code_repo_has_tests` = `'tests' in test_context.get('testing', {}).get('directories', [])`
- `downstream_readiness` = `downstream_context.get('agent_readiness', 'medium')`

Invoke the **`test-plan.analyze.placement`** forked subagent to analyze test cases and recommend placement:

```python
placement_results = invoke_skill_forked(
    "test-plan.analyze.placement",
    args={
        'feature_dir': feature_dir,
        'code_repo': code_repo,
        'code_repo_readiness': code_repo_readiness,
        'code_repo_has_tests': code_repo_has_tests,
        'downstream_readiness': downstream_readiness
    }
)
```

The subagent:

### Step 2: Per-TC Placement Analysis

Extract repository capabilities from Step 1:
- `code_repo_readiness` from `test_context.get('agent_readiness', 'unknown')`
- `code_repo_has_tests` from checking if 'tests' in `test_context.get('testing', {}).get('directories', [])`
- `downstream_readiness` from `downstream_context.get('agent_readiness', 'medium')`

Invoke **`test-plan.analyze.placement`** forked subagent:

```python
placement_decisions = invoke_skill_forked(
    "test-plan.analyze.placement",
    args={
        'feature_dir': feature_dir,
        'code_repo': code_repo,
        'code_repo_readiness': code_repo_readiness,
        'code_repo_has_tests': code_repo_has_tests,
        'downstream_readiness': downstream_readiness
    }
)
```

The subagent analyzes each TC and returns placement recommendations with:
- Test level classification (unit, integration, k8s-integration, api, e2e)
- Placement scores (same_repo, downstream, both)
- Recommended placement with reasoning
- User confirmation (accept all or review/override per TC)

**Placement Philosophy** (applied by subagent):
- **P0 strongly prefers upstream** for fast feedback (blocks PRs early)
- **K8s API ≠ Full Stack**: K8s integration tests can use envtest in component repo
- **E2E requires appropriate stack**: Mocked E2E → component repo, full-stack E2E → downstream

Store the returned placement decisions in `test_cases` list (each TC dict includes `placement_location`, `level`, `scores`, `reasons`).

If any TCs are placed `downstream` or `both`, locate downstream repository:
1. Find the downstream repo:
   ```bash
   downstream_repo_path=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py find-target "opendatahub-io/opendatahub-tests")
   ```
2. If NOT found (exit code 1): Ask user to clone it:
   ```bash
   downstream_repo_path=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py clone "<downstream_url>" "~/Code/opendatahub-tests")
   ```
3. Set `downstream_repo_path`

### Step 3: Select Test Cases to Implement

#### 3.1 Parse --test-cases argument

If `--test-cases` was provided:
1. Parse comma-separated list (e.g., `TC-API-001,TC-API-002,TC-E2E-001`)
2. Validate each TC ID exists in `test_cases/`
3. If any TC ID not found, inform user and stop
4. Set `selected_test_cases = [parsed TC IDs]`
5. Set `mode = "selective"`

If `--test-cases` was NOT provided:
1. Read all TC IDs from `test_cases/INDEX.md`
2. Set `selected_test_cases = [all TC IDs]`
3. Set `mode = "batch"`

Present summary:
- If selective: `Implementing <N> selected test case(s): <TC IDs>`
- If batch: `Implementing ALL test cases for feature: <feature_name>. Total: <N> test cases`

Show counts by priority (P0/P1/P2) and by category.

Ask for confirmation via AskUserQuestion: `Proceed? [yes/no]`

#### 3.2 Filter already-implemented test cases

For each selected TC:
1. Read frontmatter using `scripts/utils/read_frontmatter(tc_file)`
2. Check if `automation_status == 'Implemented'` OR `implementation_status == 'implemented'`
3. If already implemented: add to `already_implemented` list
4. Else: add to `to_implement` list

If `already_implemented` is not empty:
1. Warn user: `Skipping <N> already-implemented test case(s): <TC IDs>`
2. Ask via AskUserQuestion: `Re-implement these test cases? [yes/no]`
   - If **yes**: move them to `to_implement`
   - If **no**: skip them

Set `selected_test_cases = to_implement`

#### 3.3 Read and parse TC files

For each TC in `selected_test_cases`:
1. Use `scripts/utils/parse_tc_file(tc_file)` to read and parse
2. Store in `test_cases` list as dict with all TC data + placement decisions from Step 2.2

### Step 4: Map Test Cases to Test Files

#### 4.1 Determine file organization strategy

Analyze test file organization from conventions:

1. **If `use_odh_context == True`**: Check `test_context['testing']` for explicit patterns:
   - If `test_directory` shows subdirectories like `tests/unit/`, `tests/integration/`, `tests/api/` → respect that structure, use `org_pattern = "by-category-with-subdirs"`
   - If `test_directory` shows flat structure → use default below

2. **Default**: `org_pattern = "by-category"` (one file per category, flat structure)
   - Example: `test_api_<feature>.py`, `test_cfg_<feature>.py`, `test_sec_<feature>.py`
   - Keeps files manageable (typically 10-15 test functions per file)
   - Groups related tests together

3. **If pattern unclear from conventions**, ask user via AskUserQuestion:
   > How should test files be organized?
   > 1. Group by category - one file per category (test_api_feature.py) — **Recommended**
   > 2. One file per test case (test_tc_api_001.py)
   > 3. Group by endpoint (test_jobs_endpoint.py)

Map choice to `org_pattern`: `by-category`, `one-per-tc`, `by-endpoint`

#### 4.2 Create file mapping

Based on `org_pattern`:

**If `org_pattern == "one-per-tc"`**:
- For each TC:
  - Generate file path: `<test_dir>/test_<tc_id_lowercase>.py`
  - Generate function name: `test_<tc_id_lowercase>`
  - Create mapping entry: `{file_path, test_cases: [tc], function_names: [function_name]}`

**If `org_pattern == "by-category"`**:
- Group TCs by category (TC-API, TC-CFG, TC-SEC, etc.)
- For each category:
  - Generate file path: `<test_dir>/test_<category_lowercase>_<feature_name>.py` (flat, no subdirectories)
  - For each TC in category: generate function name: `test_<tc_description_snake_case>`
  - Create mapping entry: `{file_path, test_cases: [list of TCs], function_names: [list of function names]}`
  - Example: `tests/test_api_metrics.py` contains all TC-API-001, TC-API-002, etc.

**If `org_pattern == "by-category-with-subdirs"`** (when repo conventions require it):
- Group TCs by category
- For each category:
  - Generate file path: `<test_dir>/<category_lowercase>/test_<feature_name>.py`
  - Example: `tests/api/test_metrics.py`, `tests/cfg/test_metrics.py`

**If `org_pattern == "by-endpoint"`**:
- Group TCs by endpoint (from TC.endpoints)
- For each endpoint:
  - Generate file path: `<test_dir>/test_<endpoint_sanitized>.py`
  - For each TC: generate function name
  - Create mapping entry

Present file mapping table:

```
==========================================
Test File Mapping
==========================================
File                                      Test Cases
----------------------------------------------------------
tests/api/test_notebooks_api.py          TC-API-001, TC-API-002
tests/e2e/test_notebooks_e2e.py          TC-E2E-003, TC-E2E-004
tests/unit/test_notebooks_unit.py        TC-UNIT-001, TC-UNIT-002
==========================================
```

Ask for confirmation via AskUserQuestion: `Proceed with this mapping? [yes/no]`

### Step 5: Generate Test Code

**First, identify common setup requirements (before generating tests):**

Use `scripts/utils/test_analyzer.py::identify_common_setup_requirements(test_cases)`:
- Extracts all preconditions from all TCs
- Identifies preconditions used by 2+ TCs
- Returns list sorted by usage count

Store: `common_setup_requirements`

This will be passed to the sub-agent so it can generate fixtures/setup functions.

---

For each entry in `file_mapping`:

#### 5.1 Check if file and test function exist

1. Get full path: `<code_repo_path>/<file_path>` (or `<downstream_repo_path>/<file_path>` for downstream TCs)

2. **If file exists**:
   - Read existing content
   - **Check if test function already exists** for each TC in this file:
     ```python
     for tc, function_name in zip(test_cases_for_file, function_names):
         # Search for function definition in existing content
         pattern = f"def {function_name}\\("
         if re.search(pattern, existing_content):
             # Test is already implemented!
             tc['already_implemented'] = True
             tc['existing_function'] = function_name
             tc['existing_file'] = file_path
             print(f"  ✓ {tc['id']}: Test function '{function_name}' already exists in {file_path}")
         else:
             tc['already_implemented'] = False
     ```
   - Separate TCs into: `already_implemented` and `needs_implementation`
   - **Sync automation status for already-implemented TCs**:
     ```python
     for tc in already_implemented:
         # Update TC frontmatter to reflect current state
         result=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py set <feature_dir>/test_cases/<tc['id']>.md \
             automation_status="Complete" \
             automation_file="<tc['existing_file']>" \
             automation_function="<tc['existing_function']>" 2>&1)
         
         if [ $? -eq 0 ]; then
             print(f"  → Updated {tc['id']} frontmatter: automation_status=Complete")
         else
             echo "Warning: Failed to update {tc['id']} frontmatter: $result"
             # Ask user via AskUserQuestion whether to continue or stop
         fi
     ```
   - Set `mode = "append"` (only for `needs_implementation` TCs)
   
3. **If file does NOT exist**:
   - All TCs in this file: `already_implemented = False`
   - Set `mode = "create"`
   - Need to generate file header

4. **Ask user for confirmation** if some tests are already implemented:
   If `already_implemented` list is not empty:
   ```
   ✓ Found <N> already-implemented test(s) in <file_path>:
     - TC-API-001: test_create_notebook_positive()
     - TC-API-002: test_create_notebook_invalid_params()
   
   These TC frontmatter files will be updated to reflect automation_status=Implemented.
   
   Options:
   1. **Skip them** - Only implement missing tests
   2. **Re-generate** - Overwrite existing test functions
   3. **Review** - Show me the existing implementations first
   
   Choice [1/2/3]:
   ```
   
   - If **Skip** (option 1): Only generate functions for `needs_implementation` TCs
   - If **Re-generate** (option 2): Generate all functions (will overwrite existing)
   - If **Review** (option 3): Show existing function code, then ask again

Store: `mode` ("create" or "append"), `needs_implementation` list, `already_implemented` list

#### 5.2 Generate file header (if mode == "create")

Based on `framework` and `conventions`:

For pytest:
```python
"""
Test cases for <feature_name>

Strategy: <source_key>
Test Plan: <link to TestPlan.md or PR>
"""

import pytest
# Add imports based on conventions

# Fixtures (if any common setup)
```

Adapt header based on linting tools, import style from conventions.

#### 5.3 Generate test functions via forked sub-agents (PARALLEL)

**Invoke forked sub-agent `test-plan.create.test-function` for each TC in parallel:**

**NOTE**: `common_setup_requirements` was already identified at the beginning of Step 5 and will be passed to each sub-agent.

```python
# Launch ALL sub-agents in parallel (one per TC)
for tc in test_cases_for_file:
    invoke_skill_forked(
        "test-plan.create.test-function",
        args={
            'tc_file': tc['file'],
            'function_name': function_names[i],
            'framework': framework,
            'conventions_file': f"{feature_dir}/test_implementation_conventions.md",
            'pattern_guide': testing_pattern_guide if testing_pattern_guide else None,
            'repo_instructions_file': repo_instructions_file if repo_instructions_file else None,  # From Step 1.2b Step 0
            'common_setup': common_setup_requirements,  # From Step 6
            'target_repo': code_repo_path,
            'placement': tc['placement_location']
        }
    )

# Wait for all sub-agents to complete
# Each returns: Test function code (framework-specific) + fixture code if needed
```

Sub-agent receives:
- TC spec (full content)
- Function name to generate
- Framework (pytest, unittest, etc.)
- Conventions to follow
- Pattern guide (Tiger Team)
- Repo-specific instructions (CLAUDE.md, AGENTS.md, CONSTITUTION.md - if available)
- Target repo context
- Placement (same_repo/downstream)

Sub-agent returns:
- Python test function code (decorator + def + docstring + implementation)

Store all returned functions in `test_functions` list.

#### 5.4 Assemble file content

If `mode == "create"`:
- `final_content = file_header + "\n\n" + "\n\n".join(test_functions)`

If `mode == "append"`:
- `final_content = existing_content + "\n\n" + "\n\n".join(test_functions)`

#### 5.5 Validate Python syntax

Run `python -m py_compile` on the generated content:
```bash
echo '<final_content>' > /tmp/test_file.py
python -m py_compile /tmp/test_file.py
```

If syntax is valid: proceed to Step 5.6
If syntax is INVALID:
- Save as draft: `files_to_write[full_path + '.draft'] = final_content`
- Warn user: `Syntax validation failed for <file_path> - saved as .draft for manual review`
- Skip Step 5.6 for this file (cannot score invalid syntax)

#### 5.6 Score test quality and auto-revise if needed

For each generated test file (with valid syntax):

1. **Set up score output directory**:
   ```bash
   mkdir -p <feature_dir>/test_scores
   ```

2. **Invoke forked sub-agent `test-plan.score.test-function`** for quality assessment:
   ```
   test-plan.score.test-function \
     --test-code-file <temp_test_file> \
     --tc-file <tc_file> \
     --conventions-file <conventions_file> \
     --framework <framework> \
     --output-file <feature_dir>/test_scores/<tc_id>_score.md
   ```

3. **Read score assessment** from `<feature_dir>/test_scores/<tc_id>_score.md`:
   - Extract verdict from `**Verdict**: {verdict}` line
   - Extract total score from `**Total Score**: {score}/10` line
   - Extract issues from `### Issues Found` section (everything after that heading until next `###`)

4. **Handle verdict**:

   **If verdict == "Ready" or "Good"** (score 7-10):
   - Add to `files_to_write`
   - Log: "✓ Test quality score: {score}/10 ({verdict})"

   **If verdict == "Revise"** (score 4-6):
   - Log: "⚠ Test quality score: {score}/10 - auto-revising"
   - Extract issues from score file (read `### Issues Found` section and `### Revision Needed` section)
   - Re-invoke `test-plan.create.test-function` sub-agent with same args (tc_file, conventions, pattern_guide, repo_instructions_file, etc.) plus feedback:
     ```
     Additional instructions based on quality assessment:

     {paste full "### Issues Found" section from score file}

     {paste "Specific improvements needed" from "### Revision Needed" section}
     ```
   - Save revised code to temp file
   - Re-invoke scorer with `--output-file <feature_dir>/test_scores/<tc_id>_score_revised.md`
   - Read revised score file to get new verdict and score
   - If revised score >= 7: Accept revised code
   - If revised score still < 7: Accept anyway (attempted revision), log warning

   **If verdict == "Rework"** (score 0-3):
   - Log: "❌ Test quality score: {score}/10 - significant issues"
   - Extract issues from score file (read `### Issues Found` section)
   - Save test code as draft: `<test_file_path>.draft`
   - Save score assessment: `<feature_dir>/test_scores/<tc_id>_score.md` (already written by scorer)
   - Show issues to user:
     ```
     Test {tc_id} requires manual review (score {score}/10):
     {paste issues from score file}

     Draft saved to: {test_file_path}.draft
     Score details: {score_file_path}
     ```

5. **Present quality report** to user after all tests scored:
   ```
   Test Quality Summary:
   - {N} tests scored 9-10 (Ready)
   - {N} tests scored 7-8 (Good)
   - {N} tests auto-revised (initially 4-6, revised to 7+)
   - {N} tests flagged for manual review (score 0-3)
   ```

### Step 6: Write Tests to Repositories

#### 6.1 Write test files

For each entry in `files_to_write`:
1. Create parent directories: `mkdir -p <dirname>`
2. Write file content
3. Run syntax check: `python -m py_compile <file_path>`
4. If syntax check fails, warn user but continue

#### 6.2 Validate imports in repo context

For each written file:
1. Try importing in the target repo's Python environment:
   ```bash
   cd <target_repo_path>
   python -c "import sys; sys.path.insert(0, '.'); exec(open('<file_path>').read())"
   ```
2. If import fails, warn user with error message but do not block

#### 6.3 Container validation (optional)

If `validate_in_container == True`:

1. **Start container**:
   ```bash
   podman run -d --name test-context-<repo_name>-validation \
     -v <target_repo_path>:/app:Z \
     -w /app \
     <validation_recipe.base_image> \
     sleep infinity
   ```

2. **Install system dependencies**:
   ```bash
   podman exec test-context-<repo_name>-validation bash -c \
     "apt-get update && apt-get install -y <system_deps>"
   ```

3. **Run setup commands** from `validation_recipe.setup_commands`

4. **Run lint on generated files**:
   Report lint results (pass/fail)

5. **Run tests on generated files**:
   For each generated test file, run pytest and report results

6. **Cleanup container**:
   ```bash
   podman rm -f test-context-<repo_name>-validation
   ```

Present validation summary to user.

### Step 7: Update Test Case Frontmatter and Present Summary

For each TC in `test_cases`:

1. Find the test file and function for this TC from `file_mapping`
2. Update TC frontmatter using frontmatter script:
   ```bash
   uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py set <feature_dir>/test_cases/<tc_id>.md \
       automation_status="Complete" \
       automation_file="<relative_path_to_test_file>" \
       automation_function="<test_function_name>"
   ```
   
   If the command fails with a validation error:
   - Show the error to the user
   - Ask via AskUserQuestion:
     > Frontmatter update failed for {tc_id}:
     > {error message}
     >
     > Options:
     > 1. Skip frontmatter update (test is generated, just not tracked in TC file)
     > 2. Fix field values manually and retry
     > 3. Stop execution
   - Handle user choice accordingly

If feature source is a GitHub branch:
1. Commit updated TC files back to the branch:
   ```bash
   git add <feature_dir>/test_cases/
   git commit -m "test-plan(<source_key>): mark TCs as implemented"
   git push origin <branch_name>
   ```

#### 7.2 Present Summary Report

Display summary to user:

```markdown
==========================================
Test Implementation Summary
==========================================

Feature: <feature_name>
Strategy: <source_key>
Test Cases Implemented: <count>
Target Repository: <code_repo_path>
Downstream Repository: <downstream_repo_path> (if applicable)

Files Created
----------------------------------------------------------
File                                  Test Cases       LOC
tests/api/test_notebooks_api.py      TC-API-001,002   120
tests/e2e/test_notebooks_e2e.py      TC-E2E-003,004   200
tests/unit/test_notebooks_unit.py    TC-UNIT-001,002   80

Test Case Status
----------------------------------------------------------
TC ID          Category  Priority  Automated  File
TC-API-001     API       P0        ✅          tests/api/test_notebooks_api.py
TC-API-002     API       P1        ✅          tests/api/test_notebooks_api.py
TC-E2E-003     E2E       P0        ✅          tests/e2e/test_notebooks_e2e.py
...

Test Quality
----------------------------------------------------------
- <N> tests scored 9-10 (Ready - excellent quality)
- <N> tests scored 7-8 (Good - minor improvements)
- <N> tests auto-revised (improved from 4-6 to 7+)
- <N> tests flagged for review (score 0-3)

Suggested Fixtures (if any common setup found)
----------------------------------------------------------
{for each common requirement from Step 6}
- '<requirement>' used by <count> TCs (<used_by_tcs>)
  → Consider extracting to fixture/setup function

Next Steps
----------------------------------------------------------
1. Review generated tests: cd <target_repo_path>
2. Run tests locally: pytest <test_files>
3. Address TODOs: Search for # TODO: in generated files
4. Create fixtures for common setup (if suggested above)
5. Commit and create PR:
   cd <target_repo_path>
   git checkout -b test/<feature_name>
   git add <test_files>
   git commit -m "Add automated tests for <feature_name> (<source_key>)"
   git push origin test/<feature_name>
   gh pr create --title "Automated tests for <feature_name>" --body "Implements test cases from <test_plan_pr_url>"

✓ Test implementation complete

Target repository: <target_repo_path>
Downstream repository: <downstream_repo_path> (if applicable)
==========================================
```

---

**For reference documentation** (sub-agents, utility scripts, dependencies, architecture), see [README.md](README.md).

$ARGUMENTS
