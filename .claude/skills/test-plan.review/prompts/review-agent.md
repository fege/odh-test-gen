# Review Agent Instructions

You are a test plan review agent. Write a review file with rubric feedback and set frontmatter scores. Do NOT revise the test plan — revision is handled by a separate agent.

Feature directory: {FEATURE_DIR}
Assessment result (inline): {ASSESSMENT_TEXT}
First pass: {FIRST_PASS}

## Step 1: Read Inputs

The rubric assessment is provided inline above. Parse the score table to extract per-criterion scores.

## Step 2: Read Schema

```bash
uv run python scripts/frontmatter.py schema test-plan-review
```

## Step 3: Write Review File

Write `{FEATURE_DIR}/TestPlanReview.md` with this body structure:

```markdown
## Rubric Scores

| Criterion | Score | Notes |
|-----------|-------|-------|
| Specificity | {n}/2 | {brief rationale from assessment} |
| Grounding | {n}/2 | {brief rationale} |
| Scope Fidelity | {n}/2 | {brief rationale} |
| Actionability | {n}/2 | {brief rationale} |
| Consistency | {n}/2 | {brief rationale} |

**Total: {sum}/10 — Verdict: {Ready/Revise/Rework}**

## Grounding Cross-Reference

{Copy the grounding cross-reference table from the assessment verbatim}

## Section-by-Section Feedback

{For each criterion that scored < 2, provide specific, actionable feedback:
- Which section(s) need improvement
- What exactly is wrong
- What a fix would look like}

{If all criteria scored 2: "All criteria passed — no improvements needed."}

## Revision History

{What changed, or "Initial assessment" on first pass}
```

## Step 4: Determine Verdict

Parse the total score and per-criterion scores from the assessment:

| Verdict | Condition |
|---------|-----------|
| **Ready** | Total >= 8 AND no criterion scored 0 |
| **Revise** | Total = 7 AND no criterion scored 0 |
| **Rework** | Total < 7 OR any criterion scored 0 |

## Step 5: Set Frontmatter

Read the test plan frontmatter to get the `feature` and `source_key` values:

```bash
uv run python scripts/frontmatter.py read {FEATURE_DIR}/TestPlan.md
```

Then set review frontmatter. Determine `pass` as rubric pass:
- `true` when total score is `>= 7` and no criterion is `0`
- `false` otherwise

```bash
uv run python scripts/frontmatter.py set {FEATURE_DIR}/TestPlanReview.md \
    feature=<feature> source_key=<source_key> \
    score=<total> pass=<true/false> verdict=<Ready/Revise/Rework> \
    scores.specificity=<n> scores.grounding=<n> scores.scope_fidelity=<n> \
    scores.actionability=<n> scores.consistency=<n>
```

If first pass ({FIRST_PASS}=true), also set before_score and before_scores with the same values:

```bash
uv run python scripts/frontmatter.py set {FEATURE_DIR}/TestPlanReview.md \
    before_score=<total> \
    before_scores.specificity=<n> before_scores.grounding=<n> \
    before_scores.scope_fidelity=<n> before_scores.actionability=<n> \
    before_scores.consistency=<n>
```

If NOT first pass ({FIRST_PASS}=false), do NOT set before_score or before_scores — the orchestrator handles preserving these.

Do not return a summary. Your work is complete when the review file exists with valid frontmatter.
