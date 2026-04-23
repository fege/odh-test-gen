---
name: test-plan.create-cases
description: Generate individual test case files from an existing test plan. Use after /test-plan.create to produce TC-*.md files, INDEX.md, and update the test plan.
user-invocable: true
model: opus
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Test Case Generator

Generate individual test case specification files from an existing test plan.

## Usage

```
/test-plan.create-cases [FEATURE_DIR]
```

Examples:
- `/test-plan.create-cases` (auto-detects from prior `/test-plan.create` run)
- `/test-plan.create-cases mcp_catalog`
- `/test-plan.create-cases /path/to/feature_dir`

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **First argument** (optional): Feature source - can be:
   - Local directory path: `mcp_catalog` or `/path/to/mcp_catalog`
   - GitHub branch: `https://github.com/org/repo/tree/test-plan/RHAISTRAT-400`
   - GitHub PR: `https://github.com/org/repo/pull/5`
2. **`--output-dir`** (optional): Force creation in specified directory (contributor override, skips validation)

### Auto-detection from session
If no arguments are provided, check for session context from `/test-plan.create`:
```bash
# Check if TEST_PLAN_OUTPUT_DIR environment variable is set
if [ -n "$TEST_PLAN_OUTPUT_DIR" ]; then
    # /test-plan.create was just run in this session
    feature_dir="$TEST_PLAN_OUTPUT_DIR/<feature_name>"
    echo "✓ Auto-detected from /test-plan.create session: $feature_dir"
    # Proceed directly to Step 1 (skip Step 0.2)
fi
```

### Interactive fallback
If no arguments AND no session context, ask the user via AskUserQuestion:
> **Where is the TestPlan.md located?**
>
> You can provide:
> - Local directory path (e.g., `~/Code/collection-tests/mcp_catalog`)
> - GitHub branch URL (e.g., `https://github.com/org/repo/tree/test-plan/RHAISTRAT-400`)
> - GitHub PR URL (e.g., `https://github.com/org/repo/pull/5`)

## Process

### Step 0: Pre-flight Check


#### 0.1 Python dependencies

Run `uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py schema test-case` via Bash. If it fails with a PyYAML import error, ask the user to install dependencies:
```
uv pip install -r requirements.txt
```
Do NOT proceed until this succeeds.

#### 0.2 Locate Feature Directory

**Skip this step if session context was found** (see "Auto-detection from session" above).

**If feature source is a local directory path:**

1. **Check for `--output-dir` flag**:
   - If present: use that directory and skip validation (contributor override)
   - Set `FORCE_OUTPUT_DIR=true`

2. **Validate against skill repository** (unless `FORCE_OUTPUT_DIR=true`):
   ```bash
   # Export CLAUDE_SKILL_DIR so functions in the script can use it
   export CLAUDE_SKILL_DIR

   # Load validation utilities (via symlink)
   source ${CLAUDE_SKILL_DIR}/scripts/skill_repo_guard.sh

   # Validate path is not in skill repo
   validate_local_path "$feature_dir" "$FORCE_OUTPUT_DIR" || exit 1
   ```

3. Verify `TestPlan.md` exists at `<feature_dir>/TestPlan.md`

4. Set `feature_dir` to the validated path

**If feature source is a GitHub URL (branch or PR):**

1. Parse the URL to extract:
   - Repository (`owner/repo`)
   - Branch name or PR number

2. If PR URL, fetch the branch name:
   ```bash
   pr_data=$(gh pr view <PR_NUMBER> --repo <owner/repo> --json headRefName)
   branch_name=$(echo "$pr_data" | jq -r '.headRefName')
   ```

3. Check if repo exists locally:
   ```bash
   repo_path=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py find "<repo_name>")
   ```

4. If found locally:
   ```bash
   cd "$repo_path"
   git fetch origin
   git checkout <branch_name> 2>/dev/null || git checkout -b <branch_name> origin/<branch_name>
   git pull origin <branch_name>
   ```
   - Set `feature_dir` to `$repo_path/<feature_name>` (extract feature name from branch or find TestPlan.md)

5. If NOT found locally:
   ```bash
   clone_path=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py clone "<repo_url>" "~/Code/<repo_name>")
   cd "$clone_path"
   git checkout <branch_name>
   ```
   - Set `feature_dir` to `$clone_path/<feature_name>`

6. Locate TestPlan.md within the repository (may be in a subdirectory)

**Note**: GitHub sources are always external repos, so no skill repo validation needed.

### Step 1: Read the Test Plan

1. Read `<feature_dir>/TestPlan.md` using the Read tool
2. Extract the `source_key` from the YAML frontmatter — this will be used in Step 3.1 to set frontmatter on each test case file
3. Extract:
   - Section 4 (Endpoints/Methods Under Test) — the full list of what needs test coverage
   - Section 2 (Test Strategy) — test levels, types, priorities to guide test case depth
   - Section 3 (Test Environment) — preconditions and test data requirements
   - Section 5.2 (Test Case Naming Convention) — the `TC-<CATEGORY>-<NUMBER>` prefixes and their meanings
   - Section 1.2 (Scope) — in-scope vs out-of-scope boundaries
   - Section 1.3 (Test Objectives) — what the tests should validate

### Step 1.5: Read Gaps (if available)

1. Check if `<feature_dir>/TestPlanGaps.md` exists (generated by `/test-plan.create`)
2. If it exists, read it to understand known limitations — do NOT create test cases for areas marked as pending or missing details
3. If it does not exist, proceed normally

### Step 2: Read the Test Case Template

1. Read the template from `${CLAUDE_SKILL_DIR}/test-case-template.md` using the Read tool
2. Follow this template structure for every generated test case
3. Omit optional sections (Preconditions, Test Data, Expected Response, Validation) when they are empty or not applicable — do not include empty sections
4. Always leave **Automation Status** and **Notes** as placeholders — they are filled later in the process

### Step 3: Design and Generate Test Cases

Process **one category at a time** from Section 5.2. For each category:

1. **Design** all test cases for that category:
   - Cover every endpoint/method from Section 4 relevant to this category
   - Include positive, negative, and boundary scenarios (per Section 2.2)
   - Assign priorities (P0/P1/P2) following the criteria in Section 2.3
   - Stay strictly within the scope defined in Section 1.2 — do NOT create test cases for out-of-scope items
   - Map back to test objectives from Section 1.3
   - Check against previously generated categories to avoid duplicating coverage

2. **Write** the `TC-<CATEGORY>-<NUMBER>.md` files for that category immediately before moving to the next. Include YAML frontmatter at the top of each file:

   ```yaml
   ---
   test_case_id: TC-<CATEGORY>-<NUMBER>
   source_key: <STRAT_KEY_FROM_TEST_PLAN>
   priority: <P0|P1|P2>
   status: Draft
   automation_status: Not Started
   last_updated: <today_date>
   ---
   ```

   - `source_key`: use the value extracted from the test plan's frontmatter in Step 1
   - Write the frontmatter directly — validation happens in Step 5.7

3. **E2E test cases (mandatory)**: After processing all categories, generate TC-E2E-*.md test cases that validate the user journeys defined in the strategy:
   - Every P0 endpoint from Section 4 MUST be covered by at least one E2E scenario
   - Each E2E test case should represent a complete user journey, not just a single endpoint call
   - Use `TC-E2E-<NUMBER>` naming convention (e.g., TC-E2E-001, TC-E2E-002)

This category-by-category approach ensures cross-category awareness (no duplicate coverage) while keeping each batch focused.

**Anti-hallucination rules:**
- Do NOT invent requirements not present in the test plan
- Do NOT create test cases for endpoints marked as "pending details" in Section 4
- If the test plan is ambiguous about what to test, ask the user via AskUserQuestion

### Step 4: Generate Index

After all categories are complete:

1. Create `<feature_dir>/test_cases/` directory if it doesn't already exist: `mkdir -p <feature_dir>/test_cases`
2. Each test case file must be **self-contained** — a tester should be able to execute it without reading the test plan
3. Use **realistic test data**, not placeholder values like "example.com" or "test123"
4. Generate `<feature_dir>/test_cases/INDEX.md` with:
   - Quick stats (total test cases, P0/P1/P2 counts)
   - Test cases organized by category in tables with columns: Test Case ID (linked), Title, Priority
   - Links to the parent TestPlan.md

### Step 5: Update the Test Plan

Update `<feature_dir>/TestPlan.md` using the Edit tool:
1. **Section 5** — Update the note to reflect test cases have been generated, with a link to `test_cases/INDEX.md`
2. **Section 5.1** — Fill in the Test Case Organization table with category, test case count, and priority distribution
3. **Section 6.1** — Fill in the E2E Scenario Summary table with the generated TC-E2E-* scenarios (ID, scenario name, endpoints covered, priority)
4. **Section 6.2** — Fill in the E2E Coverage Matrix mapping each endpoint from Section 4 to its E2E scenario IDs
5. **Section 10.1** — Fill in the Test Case Summary table with counts per category and priority breakdown
6. **Section 10.2** — Fill in the Test Cases column with TC IDs mapped to each endpoint. Leave the Coverage column empty — it will be filled later by `/coverage-assessment`

### Step 5.5: Update README

Update `<feature_dir>/README.md` to add a link to the test cases index:
- Add a "Test Cases" section (or update existing) with a link to `test_cases/INDEX.md`
- Include the total test case count and priority breakdown

### Step 5.6: Coverage Validation

After generating all test case files and updating the test plan, validate coverage:

1. **Endpoint coverage**: Check that every endpoint/method from Section 4 (that is NOT marked as "pending details") has at least one test case. Flag any uncovered endpoints.
2. **E2E coverage**: Verify that every P0 endpoint from Section 4 is covered by at least one TC-E2E-* test case. If any P0 endpoint lacks E2E coverage, generate the missing E2E test case(s) before proceeding.
3. **Test objective coverage**: Check that every test objective from Section 1.3 is addressed by at least one test case. Flag any uncovered objectives.
4. **Priority distribution**: Verify that P0 endpoints have P0 test cases — a critical endpoint should not only have P2 test cases.
5. **Gap cross-reference**: If `TestPlanGaps.md` was read in Step 1.5, verify that no test cases were created for endpoints or areas flagged as pending/missing. If any were, remove them and flag the inconsistency.
6. **Append to TestPlanGaps.md**: If `<feature_dir>/TestPlanGaps.md` exists, append a `## Test Case Coverage Gaps` section with any coverage gaps found (uncovered endpoints, missing objectives, priority mismatches, missing E2E scenarios). If the file does not exist, create it with just this section.

### Step 5.7: Validate Frontmatter

After all test case files are written, validate their frontmatter in one pass:

```bash
for f in <feature_dir>/test_cases/TC-*.md; do
    uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py validate "$f"
done
```

If any file fails validation, fix the frontmatter in that file and re-run the validation.

### What this skill does NOT do

- Does NOT modify the test plan's Sections 1-4, 7-9 — those are owned by `/test-plan.create`
- Does NOT fill Automation Status or Notes in TC files — those are filled later by `/coverage-assessment`
- Does NOT create test cases for out-of-scope items or pending endpoints

$ARGUMENTS
