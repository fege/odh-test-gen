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
  - mcp__atlassian__getJiraIssue
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
   uv run python ${CLAUDE_SKILL_DIR}/scripts/frontmatter.py read <feature_dir>/TestPlan.md
   ```
3. Fetch the source strategy from Jira using the `source_key`:
   ```
   mcp__atlassian__getJiraIssue with issueIdOrKey=<source_key>
   ```
   If MCP is unavailable, check for a local strategy file in `artifacts/strat-tasks/<source_key>.md`. If neither is available, warn the user and proceed — grounding and scope fidelity will be scored based on plan consistency only.

### Step 2: Score (fork)

Read the score agent prompt from `skills/test-plan-review/prompts/score-agent.md`.

Launch a **forked** score agent with substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{TEST_PLAN_PATH}` = `<feature_dir>/TestPlan.md`
- `{STRATEGY_TEXT}` = raw strategy description text from Step 1
- `{CALIBRATION_DIR}` = `skills/test-plan-review/calibration/`

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
