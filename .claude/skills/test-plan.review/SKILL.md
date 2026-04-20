---
name: test-plan.review
description: Reviews a generated test plan for completeness, consistency, and quality using a 5-criteria rubric. Scores, auto-revises, and re-scores (max 2 cycles).
user-invocable: false
model: opus
allowedTools:
  - Read
  - Write
  - Bash
  - Glob
  - Skill
  - mcp__atlassian__getJiraIssue
---

# Test Plan Reviewer

Internal orchestrator that reviews and scores a test plan using the quality rubric (5 criteria, 0-2 each, 10-point scale). Auto-revises failing plans and re-scores up to 2 times.

## Usage

This skill is not user-invocable. It is called by:
- `test-plan.create` (Step 4)
- automation/orchestrator flows that need score + auto-revision behavior

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **Feature directory** (required): path to directory containing `TestPlan.md`

### Auto-detection
If no arguments provided and `test-plan.create` just generated a test plan in this session, use that feature directory automatically.

## Process

### Step 1: Read Test Plan and Source Strategy

1. Read `<feature_dir>/TestPlan.md`
2. Read frontmatter to extract `source_key`:
   ```bash
   uv run python scripts/frontmatter.py read <feature_dir>/TestPlan.md
   ```
3. Fetch the source strategy from Jira using the `source_key`:
   ```
   mcp__atlassian__getJiraIssue with issueIdOrKey=<source_key>
   ```
   If MCP is unavailable, check for a local strategy file in `artifacts/strat-tasks/<source_key>.md` (rfe-creator convention). If neither is available, warn the user that grounding and scope fidelity scoring will be degraded, and proceed with the test plan content only.

4. Store the raw strategy text for passing to sub-agents.

### Step 2: Score (fork)

Read the score agent prompt from `${CLAUDE_SKILL_DIR}/prompts/score-agent.md`.

Launch a **forked** score agent with these substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{TEST_PLAN_PATH}` = `<feature_dir>/TestPlan.md`
- `{STRATEGY_TEXT}` = raw strategy description text from Step 1
- `{CALIBRATION_DIR}` = `${CLAUDE_SKILL_DIR}/calibration/`

The score agent evaluates the test plan against a 5-criterion rubric (specificity, grounding, scope fidelity, actionability, consistency) and returns a structured assessment with per-criterion scores and a grounding cross-reference table.

**Completeness checks performed by the score agent:**

| Section | Check |
|---------|-------|
| 1.1 Purpose | Does it clearly state what is being tested and why? |
| 1.2 Scope | Are in-scope and out-of-scope explicitly defined? |
| 1.3 Test Objectives | Are there 3-7 concrete, measurable objectives? |
| 2.1 Test Levels | Are the selected levels appropriate for the feature type? |
| 2.3 Priorities | Are P0/P1/P2 definitions specific to this feature, not generic? |
| 3.1 Cluster Config | Are versions and dependencies specified or marked TBD? |
| 3.2 Test Data | Are test data requirements concrete enough to act on? |
| 4 Endpoints/Methods | Are entries grounded in source documents, not fabricated? |
| 6.1 E2E Scenarios | Is the E2E Scenario Summary populated with TC-E2E-* entries? (Note: expected to be empty until create-cases runs) |
| 6.2 E2E Coverage | Does each P0 endpoint from Section 4 have E2E scenario coverage in Section 6.2? (Note: expected to be empty until create-cases runs) |
| 7.1 Disconnected | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
| 7.2 Upgrade | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
| 7.3 Performance | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
| 7.4 RBAC | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
| 8 Risks | Are risks specific to this feature, not boilerplate? |
| 9 Environment | Is there enough detail to set up a test environment? |

### Step 3: Review (fork)

Read the review agent prompt from `${CLAUDE_SKILL_DIR}/prompts/review-agent.md`.

Launch a **forked** review agent with these substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{ASSESSMENT_TEXT}` = full output from the score agent (Step 2)
- `{FIRST_PASS}` = `true` (first assessment cycle)

The review agent writes `<feature_dir>/TestPlanReview.md` with rubric scores, feedback, and validated frontmatter.

**Consistency checks performed by the review agent:**
- Do the endpoints in Section 4 align with the scope in Section 1.2?
- Do the test levels in Section 2.1 match the interface types in Section 4?
- Are priority assignments in Section 4 consistent with the definitions in Section 2.3?
- Does Section 10.2 list all endpoints from Section 4?
- Are NFR categories in Section 7 consistent with the feature scope? (e.g., a feature that pulls images should not mark Disconnected as N/A)
- Does Section 6.2 E2E Coverage Matrix include all P0 endpoints from Section 4? (Note: expected to be empty until create-cases runs)

### Step 4: Check Criteria and Revise (max 2 cycles)

After the review agent completes, read the review frontmatter:

```bash
uv run python scripts/frontmatter.py read <feature_dir>/TestPlanReview.md
```

If all five criteria in `scores.*` are `2`, proceed to Step 5 (done).

If any criterion in `scores.*` is `< 2`, enter the revision loop.

#### Revision Loop

Initialize cycle counter: `reassess_cycle=0`

**4a. Filter for revision:**

```bash
uv run python scripts/filter_for_revision.py <feature_dir>
```

If output is `SKIP`, stop the loop and proceed to Step 5.

**4b. Launch revise agent (fork):**

Read the revise agent prompt from `${CLAUDE_SKILL_DIR}/prompts/revise-agent.md`.

Launch with substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{STRATEGY_TEXT}` = raw strategy text from Step 1

The revise agent edits TestPlan.md (only sections mapped to failing criteria) and sets `auto_revised=true`.

**4c. Check if reassessment is needed:**

```bash
uv run python scripts/frontmatter.py read <feature_dir>/TestPlanReview.md
```

If `auto_revised` is `false`, the revise agent found nothing to change — stop the loop.

Increment `reassess_cycle`. If `reassess_cycle >= 2`, stop — max cycles reached. Proceed to Step 5.

**4d. Save cumulative state:**

```bash
uv run python scripts/preserve_review_state.py save <feature_dir>
```

**4e. Re-score:**

Delete the existing review file to force a clean re-assessment:
```bash
rm <feature_dir>/TestPlanReview.md
```

Repeat Step 2 (score agent) with the revised TestPlan.md.

**4f. Re-review:**

Repeat Step 3 (review agent) with `{FIRST_PASS}=false`.

**4g. Restore before_scores and revision history:**

```bash
uv run python scripts/preserve_review_state.py restore <feature_dir>
```

**4h. Check criteria again:**

Read the review frontmatter. If all criteria are now `2`, stop.
If any criterion remains `< 2` and cycles remain, go back to 4a.
If cycles are exhausted, stop and proceed to Step 5.

### Step 5: Present Results

Read the final review file and present a summary to the user:

```markdown
## Test Plan Review — {feature_name}

**Score: {score}/10 — Verdict: {verdict}**

| Criterion | Score |
|-----------|-------|
| Specificity | {n}/2 |
| Grounding | {n}/2 |
| Scope Fidelity | {n}/2 |
| Actionability | {n}/2 |
| Consistency | {n}/2 |

{If before_score differs from score:}
**Delta: {before_score} → {score} ({+/-difference})**

{If verdict = Ready:}
The test plan is ready for test case generation. Run `/test-plan.create-cases <feature_dir>` to proceed.

{If verdict = Revise (after max cycles):}
The test plan improved but still has issues. Review `<feature_dir>/TestPlanReview.md` for remaining feedback. Consider providing additional source documents (ADR, API spec) to resolve grounding gaps.

{If verdict = Rework:}
The test plan needs significant rework. This may indicate the source strategy lacks sufficient detail. Review `<feature_dir>/TestPlanReview.md` for specific issues.

{If this plan is already in an open PR and reviewer comments exist:}
Use `/test-plan.resolve-feedback <PR_URL>` to triage and apply PR feedback items.
```

## What This Skill Does NOT Do

- Does NOT generate test plans (use `/test-plan.create`)
- Does NOT generate test cases (use `/test-plan.create-cases`)
- Does NOT modify the source strategy
- Does NOT submit anything to Jira
- Does NOT resolve GitHub PR comments (use `/test-plan.resolve-feedback <PR_URL>`)

$ARGUMENTS
