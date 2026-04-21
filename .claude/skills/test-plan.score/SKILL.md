---
name: test-plan.score
description: Score an existing test plan using the quality rubric without triggering auto-revision. Useful for evaluating test plans outside the generation pipeline.
user-invocable: true
model: opus
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
/test-plan.score <feature_dir>
```

Examples:
- `/test-plan.score kagenti_agent_templates`
- `/test-plan.score mcp_catalog`

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **Feature directory** (required): path to directory containing `TestPlan.md`

## Process

### Step 0: Verify test-plan scripts are available

Check for required scripts directory:

```bash
# Try to locate test-plan scripts in order of preference
TESTPLAN_SCRIPTS=""

# 1. Current directory (if user is in test-plan repo)
if [ -f "./scripts/frontmatter.py" ]; then
    TESTPLAN_SCRIPTS="$(pwd)/scripts"
# 2. Dedicated install location (for registry users)
elif [ -d "$HOME/.claude/test-plan-scripts/scripts" ]; then
    TESTPLAN_SCRIPTS="$HOME/.claude/test-plan-scripts/scripts"
# 3. Common dev location
elif [ -d "$HOME/Code/test-plan/scripts" ]; then
    TESTPLAN_SCRIPTS="$HOME/Code/test-plan/scripts"
fi

# Verify scripts exist
if [ -z "$TESTPLAN_SCRIPTS" ] || [ ! -f "$TESTPLAN_SCRIPTS/frontmatter.py" ]; then
    cat <<'SETUP_MSG'
❌ Test-plan scripts not found

This skill requires Python utility scripts. Please set up:

Option 1 (Recommended - for registry users):
  git clone https://github.com/fege/test-plan ~/.claude/test-plan-scripts
  cd ~/.claude/test-plan-scripts
  uv pip install -e ".[dev]"

Option 2 (For contributors):
  git clone https://github.com/fege/test-plan ~/Code/test-plan
  cd ~/Code/test-plan
  uv pip install -e ".[dev]"

Then re-run this skill.
SETUP_MSG
    exit 1
fi

echo "✓ Using scripts from: $(dirname $TESTPLAN_SCRIPTS)"
```

Store: `TESTPLAN_SCRIPTS` (absolute path to scripts directory)

### Step 1: Read Test Plan and Source Strategy

1. Read `<feature_dir>/TestPlan.md`
2. Read frontmatter to extract `source_key`:
   ```bash
   uv run python $TESTPLAN_SCRIPTS/frontmatter.py read <feature_dir>/TestPlan.md
   ```
3. Fetch the source strategy from Jira using the `source_key`:
   ```
   mcp__atlassian__getJiraIssue with issueIdOrKey=<source_key>
   ```
   If MCP is unavailable, check for a local strategy file in `artifacts/strat-tasks/<source_key>.md`. If neither is available, warn the user and proceed — grounding and scope fidelity will be scored based on plan consistency only.

### Step 2: Score (fork)

Read the score agent prompt from `.claude/skills/test-plan.review/prompts/score-agent.md`.

Launch a **forked** score agent with substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{TEST_PLAN_PATH}` = `<feature_dir>/TestPlan.md`
- `{STRATEGY_TEXT}` = raw strategy description text from Step 1
- `{CALIBRATION_DIR}` = `.claude/skills/test-plan.review/calibration/`

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
{If = 7, no zeros: "**Revise** — minor improvements needed. Re-run via `/test-plan.create` flow to apply auto-revision, or invoke the internal `test-plan.review` workflow from automation."}
{If < 7 or any zero: "**Rework** — significant issues. Re-run via `/test-plan.create` flow for remediation, or use automation that calls internal `test-plan.review`."}

### Grounding Cross-Reference
{Include the full grounding cross-reference table from the scorer}
```

## What This Skill Does NOT Do

- Does NOT write a TestPlanReview.md file
- Does NOT trigger auto-revision
- Does NOT modify the test plan
- For scoring + auto-revision, use `/test-plan.create` flow (which calls internal `test-plan.review`)

$ARGUMENTS
