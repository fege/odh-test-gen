---
name: test-plan-review
description: Reviews a generated test plan for completeness, consistency, and quality using a 5-criteria rubric. Scores, auto-revises, and re-scores (max 2 cycles). Use for automated quality assessment and iterative improvement of generated test plans.
user-invocable: false
model: opus
allowedTools:
  - Read
  - Write
  - Bash
  - Glob
  - Skill
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
       echo "ERROR: scripts/resolve_strategy.py failed to resolve the source strategy — stopping review." >&2
       echo "$resolve_result" >&2
       exit 1
   fi

   strategy_file_path=$(echo "$resolve_result" | jq -r '.strategy_file')
   ```

   `strategy_file_path` is the persistent, local-only snapshot — it is never removed (not at Step
   5, not across any re-score cycle) and is reused as-is on every re-score in Step 4e.

4. Compute interface coverage and AC/NFR citation validity deterministically (Section 9.2/6.2 vs Section 4 is a mechanical table diff, and citation validity is a mechanical STRAT cross-check — neither is an LLM judgment call). This is delegated to `scripts/build_citation_inputs.py`, which derives `ac_count`/`nfr_categories` from `strategy_file_path` and calls the three validators directly:

   ```bash
   gate_result=$(cd "$repo_root" && uv run python scripts/build_citation_inputs.py <feature_dir> --strategy-file "$strategy_file_path") || {
       echo "ERROR: scripts/build_citation_inputs.py failed to construct citation gate inputs — stopping review." >&2
       echo "$gate_result" >&2
       exit 1
   }

   interface_coverage_result=$(echo "$gate_result" | jq -c '.interface_coverage_result')
   ac_citations_result=$(echo "$gate_result" | jq -c '.ac_citations_result')
   ac_coverage_result=$(echo "$gate_result" | jq -c '.ac_coverage_result')
   ```

   A nonzero exit means gate-input construction itself failed (unreadable strategy file, a parsing bug) — that's an execution failure, not data about the test plan, so stop rather than silently falling back to degraded mode. With the pre-create-cases guards, `valid: true` is expected before test cases exist — both Section 9.2 (Test Cases column blank) and Section 6.2 are recognized as not-yet-populated and skipped. A `valid: false` here signals a genuine coverage gap; pass it as data to the score agent.

5. Resolve `additional_docs` from TestPlan.md frontmatter deterministically — path validation and file reading happen in Python, not in the LLM prompt. The script reads frontmatter itself (the LLM is not in the trust path for path resolution):

   ```bash
   additional_docs_raw=$(cd "$repo_root" && uv run python scripts/resolve_additional_docs.py <feature_dir>) || {
       echo "ERROR: scripts/resolve_additional_docs.py failed — stopping review." >&2
       echo "$additional_docs_raw" >&2
       exit 1
   }

   additional_docs_result=$(echo "$additional_docs_raw" | jq -c '.docs')
   ```

### Step 2: Score (fork)

Read the score agent prompt from `${CLAUDE_SKILL_DIR}/prompts/score-agent.md`.

Launch a **forked** score agent with these substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{TEST_PLAN_PATH}` = `<feature_dir>/TestPlan.md`
- `{STRATEGY_FILE_PATH}` = `strategy_file_path` from Step 1
- `{CALIBRATION_DIR}` = `${CLAUDE_SKILL_DIR}/calibration/`
- `{INTERFACE_COVERAGE_RESULT}` = JSON from Step 1 (`interface_coverage_result`)
- `{AC_CITATIONS_RESULT}` = JSON from Step 1 (`ac_citations_result`)
- `{AC_COVERAGE_RESULT}` = JSON from Step 1 (`ac_coverage_result`)
- `{ADDITIONAL_DOCS_CONTENT}` = JSON from Step 1 (`additional_docs_result`)

The score agent evaluates the test plan against a 5-criterion rubric (specificity, grounding, scope fidelity, actionability, consistency) and returns a structured assessment with per-criterion scores and a grounding cross-reference table.

**Completeness checks performed by the score agent:**

| Section | Check |
|---------|-------|
| 1.1 Purpose | Does it clearly state what is being tested and why? |
| 1.2 Scope | Are in-scope and out-of-scope explicitly defined? |
| 1.3 Test Objectives | Is there at least one objective per STRAT acceptance criterion (every AC covered), plus grounded NFR objectives where applicable? |
| 2.1 Test Levels | Are the selected levels appropriate for the feature type? |
| 2.3 Priorities | Are P0/P1/P2 definitions specific to this feature, not generic? |
| 3.1 Cluster Config | Are versions and dependencies specified or marked TBD? |
| 3.2 Test Data | Are test data requirements concrete enough to act on? |
| 4 Interfaces Under Test | Are entries grounded in source documents, not fabricated? |
| 6.1 E2E Scenarios | Is the E2E Scenario Summary populated with TC-E2E-* entries? (Note: expected to be empty until create-cases runs) |
| 6.2 E2E Coverage | Does each interface from Section 4 have E2E scenario coverage in Section 6.2? Checked deterministically via `interface-coverage` (Step 1), not LLM table-reading. (Note: expected to be empty until create-cases runs) |
| 7.1 Disconnected | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
| 7.2 Upgrade | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
| 7.3 Performance | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
| 7.4 RBAC | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
| 7.5 Security | Addressed with testing considerations or explicitly marked Not Applicable with justification? |
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
- Do the interfaces in Section 4 align with the scope in Section 1.2?
- Do the test levels in Section 2.1 match the interface types in Section 4?
- Are priority assignments in Section 6.1 consistent with the definitions in Section 2.3?
- Does Section 9.2 list all interfaces from Section 4? (deterministic — from the `interface-coverage` result computed in Step 1, not re-derived)
- Are NFR categories in Section 7 consistent with the feature scope? (e.g., a feature that pulls images should not mark Disconnected as N/A)
- Does Section 6.2 E2E Coverage Matrix include all interfaces from Section 4? (deterministic — from the `interface-coverage` result; expected unpopulated until create-cases runs)

### Step 3.5: Enforce Citation Gate

The review agent is instructed to read `ac_citations_result.valid`/`ac_coverage_result.valid` directly and cap Scope Fidelity to `<= 1` when either is false — but LLM compliance with that instruction isn't guaranteed. Deterministically re-apply it, and check the result — `enforce_citation_gate.py` always exits 0 by design (so malformed input doesn't kill the review run) and reports its outcome as JSON on stdout, never bare text, so a broken gate can't be mistaken for a clean result:

```bash
repo_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)
gate_result=$(cd "$repo_root" && uv run python scripts/enforce_citation_gate.py <feature_dir> \
    --ac-citations-result "$ac_citations_result" --ac-coverage-result "$ac_coverage_result")
gate_status=$(echo "$gate_result" | jq -r '.status')

case "$gate_status" in
    overridden|ok|skip) ;;
    *)
        echo "ERROR: scripts/enforce_citation_gate.py failed — stopping review." >&2
        echo "$gate_result" >&2
        exit 1
        ;;
esac
```

If this overrides `scope_fidelity` (`gate_status = overridden`), the corrected value (and an injected feedback note explaining why) is what Step 4 evaluates below — not whatever the review agent originally wrote. Anything other than `overridden`/`ok`/`skip` — most concretely `error` (malformed `ac_citations_result`/`ac_coverage_result`, or an invalid `TestPlanReview.md`; see `gate_result`'s `.error` field) — means the gate itself failed to run: stop rather than let an unenforced score pass through.

### Step 4: Check Criteria and Revise (max 2 cycles)

After the review agent completes, read the review frontmatter:

```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py read <feature_dir>/TestPlanReview.md)
```

If all five criteria in `scores.*` are `2`, proceed to Step 5 (done).

If any criterion in `scores.*` is `< 2`, enter the revision loop.

#### Revision Loop

Initialize cycle counter: `reassess_cycle=0`

**4a. Filter for revision:**

```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/filter_for_revision.py <feature_dir>)
```

If output is `SKIP`, stop the loop and proceed to Step 5.

**4b. Launch revise agent (fork):**

Read the revise agent prompt from `${CLAUDE_SKILL_DIR}/prompts/revise-agent.md`.

Launch with substitutions:
- `{FEATURE_DIR}` = feature directory path
- `{STRATEGY_FILE_PATH}` = `strategy_file_path` from Step 1

The revise agent edits TestPlan.md (only sections mapped to failing criteria) and sets `auto_revised=true`.

**4c. Check if reassessment is needed:**

```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py read <feature_dir>/TestPlanReview.md)
```

If `auto_revised` is `false`, the revise agent found nothing to change — stop the loop.

Increment `reassess_cycle`. If `reassess_cycle >= 2`, stop — max cycles reached. Proceed to Step 5.

**4d. Save cumulative state:**

```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/preserve_review_state.py save <feature_dir>)
```

**4e. Re-score:**

Delete the existing review file to force a clean re-assessment:
```bash
rm <feature_dir>/TestPlanReview.md
```

Recompute validation results against the revised `TestPlan.md` — the revise agent (4b) may have edited Section 4, 6.2, 9.2, or citations, so all four must be refreshed before re-scoring:

```bash
repo_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)
gate_result=$(cd "$repo_root" && uv run python scripts/build_citation_inputs.py <feature_dir> --strategy-file "$strategy_file_path") || {
    echo "ERROR: scripts/build_citation_inputs.py failed — stopping review." >&2
    echo "$gate_result" >&2
    exit 1
}

interface_coverage_result=$(echo "$gate_result" | jq -c '.interface_coverage_result')
ac_citations_result=$(echo "$gate_result" | jq -c '.ac_citations_result')
ac_coverage_result=$(echo "$gate_result" | jq -c '.ac_coverage_result')

additional_docs_raw=$(cd "$repo_root" && uv run python scripts/resolve_additional_docs.py <feature_dir>) || {
    echo "ERROR: scripts/resolve_additional_docs.py failed — stopping review." >&2
    echo "$additional_docs_raw" >&2
    exit 1
}

additional_docs_result=$(echo "$additional_docs_raw" | jq -c '.docs')
```

Repeat Step 2 (score agent) with the revised TestPlan.md and the recomputed results.

**4f. Re-review:**

Repeat Step 3 (review agent) with `{FIRST_PASS}=false`, then repeat Step 3.5 (Enforce Citation Gate) against the recomputed `ac_citations_result`/`ac_coverage_result` from 4e.

**4g. Restore before_scores and revision history:**

```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/preserve_review_state.py restore <feature_dir>)
```

**4h. Check criteria again:**

Read the review frontmatter. If all criteria are now `2`, stop.
If any criterion remains `< 2` and cycles remain, go back to 4a.
If cycles are exhausted, stop and proceed to Step 5.

### Step 5: Present Results

`strategy_file_path` is the persistent snapshot — leave it in place for future re-review/re-score runs.

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
The test plan is ready for test case generation. Run `/test-plan-create-cases <feature_dir>` to proceed.

{If verdict = Revise (after max cycles):}
The test plan improved but still has issues. Review `<feature_dir>/TestPlanReview.md` for remaining feedback. Consider providing additional source documents (ADR, API spec) to resolve grounding gaps.

{If verdict = Rework:}
The test plan needs significant rework. This may indicate the source strategy lacks sufficient detail. Review `<feature_dir>/TestPlanReview.md` for specific issues.

{If this plan is already in an open PR and reviewer comments exist:}
Use `/test-plan-resolve-feedback <PR_URL>` to triage and apply PR feedback items.
```

## Anti-hallucination Rules

When reviewing and suggesting improvements, the score agent MUST follow these constraints:

**NEVER**:
- Invent resolution paths for TBDs (e.g., "check version in ADR section 3" when no ADR exists or that section doesn't specify versions)
- Add specific requirements, API endpoints, or version constraints not present in source documents
- Fabricate documentation references ("see design doc for details" when no design doc exists)
- Assume information exists in documents without verifying
- Create specificity improvements by inventing details

**ALWAYS**:
- Leave TBD as plain "TBD" if the strategy doesn't specify where to find the information
- Ground all improvements in actual source document content (strategy, ADR, additional_docs)
- Flag missing information as a gap rather than inventing a solution
- Defer to TestPlanGaps.md for unresolved items
- Only suggest changes that are directly traceable to source material

**Why these rules matter**: The reviewer's job is to assess completeness and consistency against source documents, not to fill gaps with assumptions. Inventing resolution paths or fabricating details creates false confidence - better to acknowledge gaps explicitly so they can be resolved with real documentation.

## What This Skill Does NOT Do

- Does NOT generate test plans (use `/test-plan-create`)
- Does NOT generate test cases (use `/test-plan-create-cases`)
- Does NOT modify the source strategy
- Does NOT submit anything to Jira
- Does NOT resolve GitHub PR comments (use `/test-plan-resolve-feedback <PR_URL>`)

$ARGUMENTS
