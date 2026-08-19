---
name: test-plan-case-implement
description: "Generate executable test automation code from test case specifications (default target: opendatahub-tests; override with --target-repo). Use after test cases are reviewed to create production-ready pytest code that follows repository conventions."
argument-hint: "<FEATURE_SOURCE> [--test-cases TC-ID,TC-ID] [--target-repo PATH]"
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

Generate executable test automation code (pytest, etc.) from TC-*.md test case specification files. Default target: opendatahub-tests E2E repo (override with `--target-repo`).

## Usage

```
/test-plan-case-implement <FEATURE_SOURCE> [--test-cases TC-NEG-001,TC-NEG-002] [--target-repo ~/Code/opendatahub-tests]
```

Examples:
- `/test-plan-case-implement features/notebooks/RHAISTRAT-400-notebook-spawning`
- `/test-plan-case-implement https://github.com/opendatahub-io/opendatahub-test-plans/pull/7` (GitHub PR)
- `/test-plan-case-implement test-plan/RHAISTRAT-400` (GitHub branch)
- `/test-plan-case-implement https://github.com/opendatahub-io/opendatahub-test-plans/pull/7 --test-cases TC-NEG-001,TC-NEG-002` (selective)
- `/test-plan-case-implement features/notebooks/RHAISTRAT-400 --target-repo ~/Code/opendatahub-tests`

**Note:** After publishing a test plan, artifacts only exist on the PR branch. Pass the PR URL:
```bash
/test-plan-publish
/test-plan-case-implement https://github.com/opendatahub-io/opendatahub-test-plans/pull/7
```

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **First argument** (required): Feature source - local directory, GitHub PR URL, or GitHub branch containing test case artifacts
   - Local path: `features/notebooks/RHAISTRAT-400-notebook-spawning`
   - GitHub PR: `https://github.com/org/repo/pull/7`
   - GitHub branch: `https://github.com/org/repo/tree/test-plan/RHAISTRAT-400` or `test-plan/RHAISTRAT-400`
2. **`--test-cases`** (optional): Comma-separated list of test case IDs to implement (e.g., `TC-NEG-001,TC-NEG-002,TC-E2E-001`)
3. **`--target-repo`** (optional): Override target repository (accepts local path or GitHub URL; default: opendatahub-io/opendatahub-tests)

If the first argument is missing or starts with `--`, fail with usage error showing required format and PR/local path examples.

## Process

### Step 0: Pre-flight Checks

#### 0.0 Python dependencies

Install the test-plan package (makes all scripts importable):
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv sync --extra dev)
```

If installation fails, inform the user and do NOT proceed.

#### 0.1 Locate feature directory

Parse the first argument from `$ARGUMENTS` (strip any leading/trailing whitespace, ignore flags).

If no feature source provided or first arg starts with `--`, exit with the error message from the "From arguments" section above.

If feature source is a GitHub branch or PR URL:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/repo.py locate-feature-dir "<feature_source>")
```

Extract `feature_dir` from the JSON result.

If feature source is a local path, use it directly as `feature_dir`.

#### 0.2 Run preflight checks

Run unified preflight validation and detection:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/preflight.py "$feature_dir")
```

The script returns JSON with:
- `valid` (bool) - If false, show error and stop
- `feature_dir`, `tc_count`, `testplan_frontmatter`
- `frontmatter_components`, `content_components`, `all_components`
- `repos` (component → repo mapping)
- `unique_repos` (list of detected repositories)
- `repos_from_frontmatter` (repos from Jira components - highest priority)
- `odh_test_context_path` (or null if not found)

Extract values from the JSON result for subsequent steps.

#### 0.3 Handle odh-test-context if not found

If `odh_test_context_path == "null"`, ask user via AskUserQuestion:
> odh-test-context not found. Provides test conventions for ~162 opendatahub-io repos.
>
> 1. Specify path to existing clone
> 2. Clone from GitHub to ~/Code/
> 3. Proceed without it (slower, less accurate)

Handle user choice.

#### 0.4 Determine and validate target repository

Get and validate target repo (parses --target-repo from arguments, defaults to opendatahub-io/opendatahub-tests):

```bash
target_repo=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
  uv run python scripts/validate_target_repo.py "$ARGUMENTS")
```

The script extracts `--target-repo` value from `$ARGUMENTS`, validates it, and returns the repo name or path.
If validation fails, the script exits with error.

#### 0.5 Locate target repository

Find target repo locally:
```bash
target_repo_path=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/repo.py find-target "$target_repo")
```

If not found (exit code 1), ask user to clone or specify path.

### Step 1: Load Testing Context

**IMPORTANT:** When analyzing `code_repo_path`: Read code files and use grep/bash. Do NOT import target repo dependencies (not in test-plan venv) or use inspect.signature().

#### 1.0 Load odh-test-context for code repository

Call `load_repo_test_context(repo_name, odh_test_context_path)` from [`scripts/utils/repo_utils.py`](scripts/utils/repo_utils.py).

The function:
1. Checks for `<odh_test_context_path>/tests/<repo_name>.json`
2. Returns: context dict (if found) or None (if not found)
3. Context dict contains: framework, directories, commands, conventions, linting, agent_readiness, container_recipe

Set variables:
- `test_context` = function result (dict or None)
- `use_odh_context` = True if `test_context` is not None, else False

If `test_context` exists, save it to `<feature_dir>/test_implementation_context.json` for reference.

#### 1.0b Load downstream E2E repository context

Call `load_repo_test_context('opendatahub-tests', odh_test_context_path)` from [`scripts/utils/repo_utils.py`](scripts/utils/repo_utils.py).

The function returns: context dict or None

Set `downstream_context`:
- If result is not None: use the context dict (contains framework, conventions, markers, agent_readiness)
- If result is None: use defaults: `{'testing': {'framework': 'pytest'}, 'agent_readiness': 'medium'}`

#### 1.1 Detect test framework

Get framework from target repository context:

```bash
framework=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
  uv run python scripts/get_framework.py "$target_repo" "$odh_test_context_path")
```

Returns framework name (pytest, unittest, playwright, robot, ginkgo, go-testing, jest, cypress) or "pytest" (default).

#### 1.2 Load test conventions

Extract conventions from the TARGET repository (where tests will be written).

**Important:** Load conventions from `$target_repo`, NOT `$code_repo_name`. Tests are written to the target repo, so conventions must come from there.

If `downstream_context` is not None (target repo has odh-test-context):

Extract and format conventions as markdown:
```bash
# Read existing file first (if it exists) to satisfy Write tool requirements
test -f "$feature_dir/test_implementation_conventions.md" && cat "$feature_dir/test_implementation_conventions.md" > /dev/null 2>&1 || true

# Extract repo name from org/repo format (e.g., opendatahub-io/opendatahub-tests -> opendatahub-tests)
target_repo_name=$(echo "$target_repo" | sed 's|.*/||')

# Extract target repo conventions
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/extract_and_format_conventions.py "$feature_dir" "$target_repo_name" "$odh_test_context_path") > "$feature_dir/test_implementation_conventions.md"
```

The script:
- Loads test context for TARGET repo from odh-test-context
- Saves `test_implementation_context.json` to feature_dir
- Extracts conventions (file patterns, markers, linting, etc.)
- Outputs formatted markdown

Set `conventions_file` = `<feature_dir>/test_implementation_conventions.md`

If `downstream_context` is None (target repo not in odh-test-context):
1. Conventions will be minimal (framework only, from Step 1.1)
2. Test generation will rely more heavily on Tiger Team pattern guides (Step 1.2b)
3. Generated tests may be less optimized for the specific repo
4. **Consider contributing to odh-test-context** for the target repository:
   - Repository: <https://github.com/opendatahub-io/odh-test-context>
   - Add JSON file: `tests/<target_repo>.json` with discovered framework, test directories, conventions, linting tools
   - See existing files in `tests/` directory as examples
   - Improves test quality for all future test generation

Store: `conventions` (dict or markdown content, or None if not available)

#### 1.2b Load testing pattern guides

Load repo instructions and pattern guides from TARGET repository (where tests will be written):
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/load_pattern_guides.py "$target_repo_path" "$framework")
```

Returns JSON with:
- `repo_instructions_files` - Found CLAUDE.md, AGENTS.md, CONSTITUTION.md
- `repo_instructions_content` - Combined content
- `pattern_guide_files` - Found {framework}-tests.md, testing-standards.md
- `pattern_guide_content` - Combined content
- `needs_generation` - true if no pattern guides found

**If `needs_generation == true`:**

1. Locate Tiger Team:
   ```bash
   (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/repo.py find-known tiger-team)
   ```
2. If found: Invoke `/test-rules-generator <target_repo_path>` to generate guides for the target repository
3. If not found: Ask user to clone Tiger Team or proceed without guides

**Pattern guides** describe HOW to write tests in the target repository (fixtures, naming, mocking, file organization). Passed to code generation sub-agents in Step 5.

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

### Step 2: Get Backend Test Cases to Implement

Parse `--test-cases` argument (if provided) and get backend test cases:

```bash
skill_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)

# Extract --test-cases value (returns space-separated TC IDs or empty string)
tc_arg=$(cd "$skill_root" && uv run python scripts/parse_skill_args.py --test-cases "$ARGUMENTS")

# Get backend test cases (auto-discovers all if tc_arg empty)

be_test_cases=$(cd "$skill_root" && uv run python scripts/get_filtered_tcs.py "$feature_dir" be_test_cases $tc_arg)
```

The script:
- Auto-discovers all TCs from `test_cases/` if `--test-cases` not provided
- Filters by automation_status and UI category
- Prompts to re-implement already_implemented TCs (interactive mode only, skipped in CI)
- Returns backend test cases to implement (space-separated)

Convert to array:
```bash
be_test_cases_array=($be_test_cases)
```

If empty, inform user and exit:
```
No backend test cases to implement. All are either UI tests or already implemented.
```

Present summary:
```
Implementing ${#be_test_cases_array[@]} backend test case(s): ${be_test_cases_array[@]}
```

#### 3.3 Read and parse TC files

Parse backend test cases into structured data:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
  uv run python scripts/parse_test_cases.py "$feature_dir" ${be_test_cases_array[@]})
```

Returns JSON array of TC dicts, each containing:
- All frontmatter fields (test_case_id, source_key, priority, status, automation_status, etc.)
- Parsed content: objective, preconditions, test_steps, expected_results, body

This `test_cases` array will be passed to the sub-agent in Step 5.

### Step 4: Map Test Cases to Test Files

**CRITICAL:** Call map_test_files.py script - do NOT manually create mappings or read existing test files.

#### 4.1 Determine test directory from component

Get component-specific test directory (uses first component from frontmatter):

```bash
first_component=$(echo "$frontmatter_components" | head -1)
test_dir=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
  uv run python scripts/get_component_test_dir.py "$first_component" "$target_repo_path")
```

This maps component name to directory (e.g., "AI Hub" → "tests/ai_hub"). Falls back to "tests" if component directory doesn't exist.

#### 4.2 Determine file organization strategy

Determine file organization strategy from conventions:
- If `test_context` shows subdirectories (unit/, api/, etc.) → `by-category-with-subdirs`
- Default → `by-category` (flat structure, one file per category)
- If unclear, ask user (by-category / one-per-tc)

Set `strategy` variable based on determination above.

#### 4.3 Generate file mapping

Call the script to generate file mapping:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/map_test_files.py \
    "$feature_dir" "$strategy" "$test_dir" \
    --feature-name "$feature_name" \
    --tc-ids "$(echo ${be_test_cases_array[@]} | tr ' ' ',')")
```

Parse the JSON output to extract:
- `file_mapping` - Array of {file_path, test_cases[], function_names[]}
- `strategy`, `total_test_cases`, `total_files`

The script handles:
- Grouping TCs by category
- Generating file paths based on strategy
- Generating function names from TC titles
- Checking for existing test files

**DO NOT** manually create /tmp/*.json files, read existing test files, or generate file paths yourself. Use the script output directly.

Present the mapping table to user.

### Step 5: Generate Test Code

**CRITICAL:** Invoke /test-plan-generate-test-file sub-agents in parallel (one per file) - do NOT generate code yourself.

Identify common setup requirements across the TCs being implemented:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
  uv run python scripts/analyze_common_setup.py "$feature_dir" ${be_test_cases_array[@]})
```

Returns JSON array of preconditions used by 2+ TCs (for fixture generation).

Ensure these variables are in context (sub-agents inherit them):
- `file_mapping` - Array from Step 4
- `test_cases` - Array from Step 3.3
- `framework` - From Step 1.1
- `conventions_file` - Path to conventions (from Step 1.2)
- `pattern_guide` - Content from Step 1.2b (or null)
- `repo_instructions` - Content from Step 1.2b (or null)
- `common_setup_requirements` - From analyze_common_setup.py above
- `code_repo_path` - Repository path
- `feature_dir` - Feature directory path

**Invoke sub-agents in parallel** using Skill tool (one per file in file_mapping):

For each file index i:
```
Skill(
  skill="test-plan:test-plan-generate-test-file",
  args="""{
  "file_index": {i},
  "file_path": "{file_mapping[i].file_path}",
  "test_cases": {json array of TCs for this file},
  "function_names": {file_mapping[i].function_names},
  "framework": "{framework}",
  "conventions_file": "{conventions_file}",
  "pattern_guide": "{pattern_guide or null}",
  "repo_instructions": "{repo_instructions or null}",
  "common_setup_requirements": {common_setup_requirements},
  "code_repo_path": "{code_repo_path}",
  "feature_dir": "{feature_dir}"
}"""
)
```

**All invocations in one message** for parallel execution. Sub-agents have `context: fork` (isolated, returns clean).

Sub-agents write results to `/tmp/test_plan_results/file_{i}.json`.

**Read result files** after all agents complete:

```bash
for i in $(seq 0 $((${#file_mapping[@]} - 1))); do
  result=$(cat /tmp/test_plan_results/file_${i}.json)
  # Parse: file_path, content, tc_ids, functions[], quality_summary, draft_files[], errors[]
done
rm -rf /tmp/test_plan_results/
```

Collect into `files_to_write` array. Proceed immediately to Step 6.

### Step 6: Write Tests to Repositories

**CRITICAL:** Write the files from `files_to_write` array. Do NOT generate or modify test code - just write what the sub-agents returned.

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

Build updates array from sub-agent results (ONLY for successfully implemented TCs):

**For each sub-agent result:**
- For each entry in `functions` array (these scored 4+): Create update entry
- Skip TCs in `draft_files` (scored 0-3, need manual review)
- Skip TCs in `errors` (generation failed)

Update frontmatter in bulk:
```bash
# updates.json: [{"tc_id": "TC-NEG-001", "automation_status": "Implemented", "file": "...", "function": "..."}]
echo "$updates_json" | (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/update_tc_frontmatter.py "$feature_dir" -)
```

Returns JSON with `updated_count`, `updated_tcs`, `errors`. Show any errors to user.

If feature source is a GitHub branch, stage, commit, and push updated TC files:
```bash
feature_name=$(basename "$feature_dir")
repo_root=$(git -C "$feature_dir" rev-parse --show-toplevel)
if ! publish_result=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/repo.py publish-artifacts "$repo_root" "$feature_name" "test-plan(<source_key>): mark TCs as implemented"); then
    echo "ERROR: publish-artifacts failed"; exit 1
fi
git push origin <branch_name>
```

#### 7.2 Present Summary Report

Aggregate quality data from all sub-agent results:
- Sum quality_summary metrics (ready_count, good_count, revised_count, flagged_count)
- Collect all draft_files (TCs scored 0-3)
- Collect all errors (TCs that failed generation)

Display implementation summary:
- Feature name, source key, total TC count
- Successfully implemented: TC count, files created with TC mapping
- Test quality distribution (Ready/Good/Revised/Flagged)
- Draft files requiring manual review (if any): List TC IDs with scores and reasons
- Failed TCs (if any): List TC IDs with error messages
- Suggested fixtures (if common setup found)
- Next steps (review, run tests, create PR)

$ARGUMENTS
