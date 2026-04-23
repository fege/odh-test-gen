---
name: test-plan.update
description: Update an existing test plan with new documentation (ADR, API specs, design docs). Re-analyzes, updates artifacts, bumps version, and optionally regenerates test cases.
user-invocable: true
model: opus
allowedTools:
  - Read
  - Write
  - Edit
  - Bash
  - Skill
  - AskUserQuestion
---

# Test Plan Updater

Update an existing test plan when new information becomes available (ADRs, API specs, design documents, requirement changes).

## Usage

```
/test-plan.update <SOURCE> <NEW_DOC_PATH> [<NEW_DOC_PATH>...]
```

Examples:
- `/test-plan.update ~/Code/collection-tests/mcp_catalog adr.pdf`
- `/test-plan.update https://github.com/org/repo/pull/42 api-spec.md design.md`
- `/test-plan.update https://github.com/org/repo/tree/test-plan/RHAISTRAT-400 requirements-v2.md`

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **First argument** (required): Test plan source - can be:
   - Local directory path: `mcp_catalog` or `/path/to/mcp_catalog`
   - GitHub branch: `https://github.com/org/repo/tree/test-plan/RHAISTRAT-400`
   - GitHub PR: `https://github.com/org/repo/pull/5`
2. **Remaining arguments** (at least one required): Paths to new documentation files (ADR, API spec, design doc, etc.)

### Interactive fallback
If insufficient arguments are provided, ask the user via AskUserQuestion:
> **Where is the test plan to update?**
>
> You can provide:
> - Local directory path (e.g., `~/Code/collection-tests/mcp_catalog`)
> - GitHub branch URL (e.g., `https://github.com/org/repo/tree/test-plan/RHAISTRAT-400`)
> - GitHub PR URL (e.g., `https://github.com/org/repo/pull/5`)

Then ask:
> **What new documentation should be incorporated?**
>
> Provide one or more file paths (ADR, API spec, design doc, requirements doc, etc.):

## Process

### Step 0: Pre-flight Checks


#### 0.1 Python dependencies

Run `uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py schema test-plan` via Bash. If it fails, ask the user to install the test-plan package:
```
cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)
uv pip install -e .
```
Do NOT proceed until this succeeds.

#### 0.2 Locate Test Plan

1. **Use the shared locate-feature-dir utility**:
   ```bash
   result=$(uv run python ${CLAUDE_SKILL_DIR}/scripts/repo.py locate-feature-dir "<source>")
   if [ $? -ne 0 ]; then
       echo "$result"
       exit 1
   fi

   # Parse JSON output
   feature_dir=$(echo "$result" | jq -r '.feature_dir')
   source_type=$(echo "$result" | jq -r '.source_type')
   ```

2. **Validate local paths against skill repository**:
   ```bash
   if [ "$source_type" = "local" ]; then
       # Validate against skill repository (no force flag for updates)
       export CLAUDE_SKILL_DIR
       source ${CLAUDE_SKILL_DIR}/scripts/skill_repo_guard.sh
       validate_local_path "$feature_dir" "false" || exit 1
   fi
   ```

**Note**: GitHub sources are always external repos, so no skill repo validation needed.

#### 0.3 Verify new documents exist

For each new document path provided:
```bash
if [ ! -f "$doc_path" ]; then
    echo "❌ ERROR: Document not found: $doc_path"
    exit 1
fi
```

### Step 1: Read Existing Artifacts

1. **Read `<feature_dir>/TestPlan.md`** using Read tool
   - Extract frontmatter: `source_key`, `version`, `feature`, `components`, `additional_docs`
   - Extract original strategy reference (JIRA key)
   - Store current test plan content for comparison

2. **Read `<feature_dir>/TestPlanGaps.md`** (if exists)
   - Extract existing gaps organized by section
   - Store for comparison with new gaps

3. **Read `<feature_dir>/TestPlanReview.md`** (if exists)
   - Note current score and verdict (will be re-evaluated after update)

4. **Read `<feature_dir>/README.md`**
   - Store for updating version and changelog

5. **Check for test cases**: `<feature_dir>/test_cases/INDEX.md`
   - If exists, count test cases for summary
   - Store flag `has_test_cases=true`

### Step 2: Read New Documents

For each new document path:
1. Read the document using Read tool
2. Store content with label (e.g., "ADR", "API Spec", "Design Doc" - infer from filename or ask user)
3. Add to `additional_docs` list in frontmatter

### Step 3: Re-analyze with New Material

Invoke the three analyzer skills **in parallel** using the Skill tool, passing:
- Original strategy content (from Jira via source_key, or from local cache)
- Existing additional docs (from frontmatter `additional_docs`)
- New documents (just read in Step 2)

- **`test-plan.analyze.endpoints`**: Re-extract feature scope and API endpoints
- **`test-plan.analyze.risks`**: Re-determine test levels, types, priorities, risks
- **`test-plan.analyze.infra`**: Re-identify environment, test data, infrastructure needs

Each analyzer returns:
- Updated findings for their sections
- New gaps (if any)
- Resolved gaps (if any were addressed by new docs)

### Step 4: Merge New Findings into TestPlan.md

Invoke the **`test-plan.merge`** sub-agent to intelligently merge new analyzer findings into the existing test plan:

```
Skill: test-plan.merge
Arguments:
  Old TestPlan.md: <full content from Step 1>
  New Findings from Analyzers:
    - Endpoints: <findings from Step 3>
    - Risks: <findings from Step 3>
    - Infrastructure: <findings from Step 3>
  New Documents Added: <list of new doc names from Step 2>
```

The merge sub-agent returns:
- Updated section content for Sections 1-4, 7-9
- Change summary (what was added/updated/deprecated)
- Statistics (sections updated, items added, user edits preserved)

**Apply the updates**:
1. Use Edit tool to update each modified section in TestPlan.md
2. Store the change summary for use in Step 10
3. Sections 5, 6, 10 (test cases, E2E, traceability) remain unchanged unless test cases are regenerated in Step 7

### Step 5: Resolve Gaps

Invoke the **`test-plan.resolve-gaps`** sub-agent to cross-reference old gaps with new findings:

```
Skill: test-plan.resolve-gaps
Arguments:
  Old Gaps from TestPlanGaps.md: <content from Step 1>
  New Findings from Analyzers:
    - Endpoints: <findings from Step 3>
    - Risks: <findings from Step 3>
    - Infrastructure: <findings from Step 3>
  New Documents Added: <list from Step 2>
```

The sub-agent returns:
- Resolved gaps (with which doc/finding resolved them)
- Unresolved gaps (still open)
- New gaps identified by analyzers
- Statistics (total before/after, resolved count)

**Update TestPlanGaps.md**:
1. Write the "## Resolved Gaps" section with resolved gaps
2. Write the "## Unresolved Gaps" section (or use original section names)
3. Add "## New Gaps Identified" section if any new gaps
4. Update frontmatter:
   ```bash
   # Get gap count from sub-agent statistics
   new_gap_count=<count_of_unresolved_gaps>
   
   # Update status: Open if gaps remain, Resolved if all resolved
   new_status=$([ $new_gap_count -eq 0 ] && echo "Resolved" || echo "Open")
   
   uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py set <feature_dir>/TestPlanGaps.md \
       gap_count=$new_gap_count \
       status=$new_status
   ```

### Step 6: Re-run Quality Review

Invoke **`test-plan.review`** skill with the updated feature directory:
```
/test-plan.review <feature_dir>
```

This generates a new `TestPlanReview.md` with updated score and verdict.

**Handle review output**:
1. Read the new verdict from frontmatter
2. Apply any auto-fix suggestions from the reviewer
3. Store scores for summary (will show in Step 10)

### Step 7: Ask About Test Cases

If `has_test_cases=true` (test cases exist), ask the user via AskUserQuestion:

> **New information has been incorporated into the test plan.**
>
> Changes detected:
> - <summary of what changed: new endpoints, updated risks, etc.>
>
> **Do you want to update the existing test cases?**
>
> 1. **Yes, update test cases** — regenerate affected test cases and add new ones for new coverage
> 2. **No, keep test cases as-is** — only TestPlan.md has been updated
> 3. **Review changes first** — show me the diff before deciding

If user selects option 1:
- Invoke `/test-plan.create-cases <feature_dir>` to regenerate test cases
- The skill will update existing TCs and generate new ones as needed

If user selects option 3:
- Show summary of TestPlan.md changes (what sections were updated)
- Ask again: "Update test cases now? [yes/no]"

### Step 8: Update README.md

Update the README with:
1. New version number (from Step 9 frontmatter update)
2. Updated "Last modified" date
3. Changelog entry:
   ```markdown
   ## Changelog
   
   ### v1.1.0 (2026-04-23)
   - Updated with new API specification
   - Resolved 3 gaps from TestPlanGaps.md
   - Added 2 new endpoints to Section 4
   ```

### Step 9: Version Bump and Frontmatter Update

1. **Determine version bump**:
   - Parse current version (e.g., `1.0.0`)
   - Increment minor version: `1.0.0` → `1.1.0`
   - If test cases were regenerated, increment: `1.1.0` → `1.2.0`

2. **Update TestPlan.md frontmatter**:
   ```bash
   uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py set <feature_dir>/TestPlan.md \
       version=$new_version \
       additional_docs="<updated_comma_separated_list>"
   ```

3. **Update status** if needed:
   - If was "Draft" and review verdict is "Ready" → set to "Ready for Review"
   - If was "In Review" → keep as "In Review" (PR reviewers will re-review)

### Step 10: Summary

Present final summary to user:
> **Test plan updated successfully**
>
> - **Location**: `<feature_dir>`
> - **Version**: <old_version> → <new_version>
> - **Quality score**: <old_score>/10 → <new_score>/10
> - **Verdict**: <verdict>
> - **Gaps resolved**: <N>
> - **Gaps remaining**: <M>
> - **Test cases**: <updated|unchanged>
>
> Updated artifacts:
> - TestPlan.md
> - TestPlanGaps.md
> - TestPlanReview.md
> - README.md
> - test_cases/ (if regenerated)
>
> **Next steps**:
> - Review changes: `git diff` (if in git repo)
> - Publish updates: `/test-plan.publish <feature_name>`

## What this skill does NOT do

- Does NOT create a new test plan from scratch — use `/test-plan.create` for that
- Does NOT resolve PR review feedback — use `/test-plan.resolve-feedback` for that
- Does NOT commit or push changes to GitHub — use `/test-plan.publish` after updating
- Does NOT modify the original strategy (JIRA issue) — only the test plan
- Does NOT auto-regenerate test cases without asking — always prompts user first

$ARGUMENTS
