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

### Step 1: Read Test Plan and Resolve Source Strategy

1. Read `<feature_dir>/TestPlan.md`
2. Read frontmatter to extract `source_key`:
   ```bash
   source_key=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
                uv run python scripts/frontmatter.py read <feature_dir>/TestPlan.md source_key)
   ```
3. Resolve the source strategy via the shared resolver — snapshot-primary: reads
   `<feature_dir>/.source-strategy.md` if `test-plan.create` already saved one, otherwise fetches
   from Jira and saves it there for next time. No degraded mode: if neither is available, this is
   a hard failure.
   ```bash
   repo_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)
   resolve_result=$(cd "$repo_root" && uv run python scripts/resolve_strategy.py <feature_dir> "$source_key")
   resolve_exit=$?

   if [ "$resolve_exit" -ne 0 ]; then
       echo "ERROR: scripts/resolve_strategy.py failed to resolve the source strategy — stopping." >&2
       echo "$resolve_result" >&2
       exit 1
   fi

   strategy_path=$(echo "$resolve_result" | jq -r '.strategy_file')
   ```

   `strategy_path` is the persistent, local-only snapshot — it is never deleted.

4. Compute AC/NFR citation validity and coverage deterministically (mirrors `test-plan.review` Step 1.5) via `scripts/build_citation_inputs.py`, which derives `ac_count`/`nfr_categories` from `strategy_path` and calls the three validators directly:

   ```bash
   gate_result=$(cd "$repo_root" && uv run python scripts/build_citation_inputs.py <feature_dir> --strategy-file "$strategy_path") || {
       echo "ERROR: scripts/build_citation_inputs.py failed to construct citation gate inputs — stopping." >&2
       echo "$gate_result" >&2
       exit 1
   }

   interface_coverage_result=$(echo "$gate_result" | jq -c '.interface_coverage_result')
   ac_citations_result=$(echo "$gate_result" | jq -c '.ac_citations_result')
   ac_coverage_result=$(echo "$gate_result" | jq -c '.ac_coverage_result')
   ```

   A nonzero exit means gate-input construction itself failed (unreadable strategy file, a parsing bug) — that's an execution failure, not data about the test plan, so stop rather than silently falling back to degraded mode.

### Step 2: Score (fork)

Read the score agent prompt from `skills/test-plan-review/prompts/score-agent.md`.

Launch a **forked** score agent with substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{TEST_PLAN_PATH}` = `<feature_dir>/TestPlan.md`
- `{STRATEGY_FILE_PATH}` = `strategy_path` from Step 1
- `{CALIBRATION_DIR}` = `skills/test-plan-review/calibration/`
- `{INTERFACE_COVERAGE_RESULT}` = JSON from Step 1 (`interface_coverage_result`)
- `{AC_CITATIONS_RESULT}` = JSON from Step 1 (`ac_citations_result`)
- `{AC_COVERAGE_RESULT}` = JSON from Step 1 (`ac_coverage_result`)

### Step 2.5: Enforce Citation Gate

The score agent is instructed to cap Scope Fidelity to `<= 1` when `ac_citations_result.valid`/`ac_coverage_result.valid` is false — but LLM compliance isn't guaranteed, and this skill writes no `TestPlanReview.md` for a gate to correct after the fact (unlike `test-plan.review`, which re-applies the rule via `enforce_citation_gate.py` once the file exists). Re-apply it directly against the agent's self-reported scores, before presenting anything:

```bash
repo_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)
scores_json='{"specificity": <n>, "grounding": <n>, "scope_fidelity": <n>, "actionability": <n>, "consistency": <n>}'
cap_result=$(cd "$repo_root" && uv run python scripts/cap_scope_fidelity.py \
    --scores "$scores_json" --ac-citations-result "$ac_citations_result" --ac-coverage-result "$ac_coverage_result")
cap_status=$(echo "$cap_result" | jq -r '.status')

case "$cap_status" in
    overridden|ok) ;;
    *)
        echo "ERROR: scripts/cap_scope_fidelity.py failed — stopping." >&2
        echo "$cap_result" >&2
        exit 1
        ;;
esac
```

`scores_json` is built from the score agent's Score Table (Step 2). If `cap_status` is `overridden`, Step 3 below presents `cap_result`'s `scores`/`score`/`verdict`/`pass` — not the agent's own numbers — and flags Scope Fidelity as automatically corrected.

### Step 3: Present Results

Parse the score agent's output and present the results to the user, substituting the Step 2.5 correction where it applies:

```markdown
## Test Plan Score — {feature_name}

### Rubric Scores

| Criterion | Score | Notes |
|-----------|-------|-------|
| Specificity | {n}/2 | {brief rationale} |
| Grounding | {n}/2 | {brief rationale} |
| Scope Fidelity | {n}/2 | {brief rationale, or "Automatically corrected — citation/coverage checks failed" if Step 2.5 overrode it} |
| Actionability | {n}/2 | {brief rationale} |
| Consistency | {n}/2 | {brief rationale} |

**Total: {sum}/10**

### Verdict

{If `cap_status` was `overridden`: use `cap_result.verdict`/`cap_result.pass` directly — do not re-derive from the total.}
{Otherwise — If >= 8, no zeros: "**Ready** — proceed to test case generation"}
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
