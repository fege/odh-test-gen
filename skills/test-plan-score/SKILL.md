---
name: test-plan-score
description: Score an existing test plan using the quality rubric without triggering auto-revision. Use for standalone quality assessment of test plans or evaluating test plans created outside the automated generation pipeline.
argument-hint: <feature_dir>
user-invocable: true
model: sonnet
allowedTools:
  - Read
  - Bash
  - Glob
  - Skill
---

# Test Plan Scorer

Score an existing test plan using the 5-criteria quality rubric (Specificity, Grounding, Scope Fidelity, Actionability, Consistency). This is the user-facing entrypoint for rubric evaluation.

## Usage

```
/test-plan-score <feature_dir>
```

Examples:
- `/test-plan-score kagenti_agent_templates`
- `/test-plan-score mcp_catalog`

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **Feature directory** (required): path to directory containing `TestPlan.md`

## Process

### Step 0: Python dependencies

Install the test-plan package (makes all scripts importable):
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv sync --extra dev)
```

If installation fails, inform the user and do NOT proceed. Once installed, all Python scripts will work from any directory.

### Step 1: Read Test Plan and Source Strategy

1. Read `<feature_dir>/TestPlan.md`
2. Read frontmatter to extract `source_key`:
   ```bash
   source_key=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
                uv run python scripts/frontmatter.py read <feature_dir>/TestPlan.md source_key)
   ```
3. Fetch the source strategy from Jira using the `source_key`:
   ```bash
   # Fetch strategy and save to temporary file
   strategy_file=$(mktemp)
   (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
    uv run python scripts/fetch_issue.py "$source_key" --output "$strategy_file") || {
       echo "Warning: Failed to fetch Jira issue, checking for local file..." >&2
       rm -f "$strategy_file"
       strategy_file=""
   }

   # If fetch failed, check for local strategy file. source_key comes from TestPlan.md
   # frontmatter — validate its shape and the resolved path's containment before reading, so a
   # malformed/malicious source_key can't escape artifacts/strat-tasks/ via path traversal.
   if [ -z "$strategy_file" ] || [ ! -f "$strategy_file" ]; then
       strat_dir=$(realpath "$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)/artifacts/strat-tasks")
       if [[ "$source_key" =~ ^[A-Z][A-Z0-9_]+-[0-9]+$ ]]; then
           local_file="$strat_dir/${source_key}.md"
       else
           local_file=""
       fi
       if [ -n "$local_file" ] && [ -f "$local_file" ] && [[ "$(realpath "$local_file")" == "$strat_dir"/* ]]; then
           strategy_content=$(cat "$local_file")
           strategy_path="$local_file"
       else
           echo "Warning: Neither Jira API nor local strategy file available. Grounding and scope fidelity will be scored based on plan consistency only." >&2
           strategy_content=""
           strategy_path=""
       fi
   else
       strategy_content=$(cat "$strategy_file")
       strategy_path="$strategy_file"
   fi
   ```

   If neither Jira API nor local file is available, warn the user and proceed — grounding and scope fidelity will be scored based on plan consistency only.

4. Compute AC/NFR citation validity and coverage deterministically (mirrors `test-plan.review` Step 1). When a strategy file is available, run `gate-inputs` then `ac-citations` + `ac-coverage` on the test plan:

   ```bash
   repo_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)

   interface_coverage_result=$(cd "$repo_root" && \
       uv run python scripts/validate.py interface-coverage <feature_dir>/TestPlan.md || true)

   if [ -n "$strategy_path" ]; then
       gate_inputs=$(cd "$repo_root" && uv run python scripts/parse_strat.py gate-inputs "$strategy_path")
       # Clean up temp file now that gate-inputs has read it
       [ -n "$strategy_file" ] && [ -f "$strategy_file" ] && rm "$strategy_file"
       ac_count=$(echo "$gate_inputs" | jq -r '.ac_count // empty')
       nfr_category_flags=()
       while IFS= read -r cat; do [ -n "$cat" ] && nfr_category_flags+=(--nfr-category "$cat"); done < <(echo "$gate_inputs" | jq -r '.nfr_categories[]? // empty')

       if [ -n "$ac_count" ]; then
           ac_citations_result=$(cd "$repo_root" && \
               uv run python scripts/validate.py ac-citations <feature_dir>/TestPlan.md --ac-count "$ac_count" "${nfr_category_flags[@]}" || true)
           ac_coverage_result=$(cd "$repo_root" && \
               uv run python scripts/validate.py ac-coverage <feature_dir>/TestPlan.md --ac-count "$ac_count" || true)
       else
           ac_citations_result=$(cd "$repo_root" && \
               uv run python scripts/validate.py ac-citations <feature_dir>/TestPlan.md || true)
       fi
   else
       # Degraded mode: presence-only citation check, no coverage
       ac_citations_result=$(cd "$repo_root" && \
           uv run python scripts/validate.py ac-citations <feature_dir>/TestPlan.md || true)
   fi
   ```

### Step 2: Score (fork)

Read the score agent prompt from `skills/test-plan-review/prompts/score-agent.md`.

Launch a **forked** score agent with substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{TEST_PLAN_PATH}` = `<feature_dir>/TestPlan.md`
- `{STRATEGY_TEXT}` = raw strategy description text from Step 1
- `{CALIBRATION_DIR}` = `skills/test-plan-review/calibration/`
- `{INTERFACE_COVERAGE_RESULT}` = JSON from Step 1 (`interface_coverage_result`)
- `{AC_CITATIONS_RESULT}` = JSON from Step 1 (`ac_citations_result`)
- `{AC_COVERAGE_RESULT}` = JSON from Step 1 (`ac_coverage_result`, or "not computed — degraded mode" if unset)

### Step 3: Present Results

Parse the score agent's output and present the results directly to the user:

```markdown
## Test Plan Score — {feature_name}

### Rubric Scores

| Criterion | Score | Notes |
|-----------|-------|-------|
| Specificity | {n}/2 | {brief rationale} |
| Grounding | {n}/2 | {brief rationale} |
| Scope Fidelity | {n}/2 | {brief rationale} |
| Actionability | {n}/2 | {brief rationale} |
| Consistency | {n}/2 | {brief rationale} |

**Total: {sum}/10**

### Verdict

{If >= 8, no zeros: "**Ready** — proceed to test case generation"}
{If = 7, no zeros: "**Revise** — minor improvements needed. Re-run via `/test-plan-create` flow to apply auto-revision, or invoke the internal `test-plan.review` workflow from automation."}
{If < 7 or any zero: "**Rework** — significant issues. Re-run via `/test-plan-create` flow for remediation, or use automation that calls internal `test-plan.review`."}

### Grounding Cross-Reference
{Include the full grounding cross-reference table from the scorer}
```

## What This Skill Does NOT Do

- Does NOT write a TestPlanReview.md file
- Does NOT trigger auto-revision
- Does NOT modify the test plan
- For scoring + auto-revision, use `/test-plan-create` flow (which calls internal `test-plan.review`)

$ARGUMENTS
