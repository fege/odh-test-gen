---
name: test-plan-create
description: Generate a test plan from a strategy (RHAISTRAT or RHOAIENG issue), with optional ADR for extra technical depth. Use when starting test planning for a new RHOAI feature with a defined Jira strategy.
argument-hint: <JIRA_KEY> [ADR_FILE_PATH]
user-invocable: true
model: opus
allowedTools:
  - Read
  - Write
  - Bash
  - Glob
  - Skill
  - AskUserQuestion
---

# Test Plan Generator

Generate a complete test plan for a RHOAI feature based on a refined strategy, and optionally an ADR document for additional technical depth.

## Usage

```
/test-plan-create <JIRA_KEY> [ADR_FILE_PATH]
```

Examples:
- `/test-plan-create RHAISTRAT-400`
- `/test-plan-create RHOAIENG-48676`
- `/test-plan-create RHAISTRAT-400 /path/to/adr.pdf`

## Inputs

Parse `$ARGUMENTS` as:
1. Required Jira key: a `RHAISTRAT-*` strategy or `RHOAIENG-*` issue.
2. Optional local ADR path (Markdown, text, or PDF).

With no arguments, use a strategy created in this session by `/strat.create` or `/strat.refine` and
proceed to Step 1. If none is available, ask for the Jira key and optional local ADR path, ADR URL
(metadata only; never fetched), and optional snake_case feature-directory name. If omitted, derive the
directory name from the feature name.

## Process

### Step 0: Pre-flight Checks

#### 0.1 Python dependencies

Install the test-plan package so all scripts are importable from any directory:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv sync --extra dev)
```

If installation fails, inform the user and **STOP**; do not proceed.

#### 0.2 Jira Environment Variables

Verify that `JIRA_URL`, `JIRA_USER`, and `JIRA_TOKEN` are configured:

```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python -c "from scripts.jira_utils import require_env; [require_env(v) for v in ('JIRA_URL','JIRA_USER','JIRA_TOKEN')]")
```

If it exits non-zero, **STOP immediately**. Do not continue or use alternative sources (MCP, cache,
web, or any workaround). Report the error and tell the user to set the missing variables: `JIRA_URL`
(base URL), `JIRA_USER` (username/email), and `JIRA_TOKEN` (API token). Otherwise proceed to Step 0.3.

#### 0.3 Determine Output Directory

**IMPORTANT**: Keep test plan artifacts outside the skill repository.

1. If `--output-dir` is present, use it as a contributor override, set `FORCE_OUTPUT_DIR=true`, and
   skip validation.

2. Otherwise, check for a saved preference:
   ```bash
   # Try to read saved preference from .claude/settings.json
   saved_dir=$(jq -r '.["test-plan"]?.output_dir // empty' .claude/settings.json 2>/dev/null)
   ```

3. Unless `--output-dir` is present, ask where to create artifacts via AskUserQuestion. If a saved
   preference exists:
   > **Where should test plan artifacts be created?**
   >
   > Press Enter to use saved location: `<saved_dir>`
   > Or provide a different directory path:

   If none exists:
   > **Where should test plan artifacts be created?**
   >
   > Provide a directory path (e.g., `~/Code/opendatahub-test-plans/plans/<team-name>`), or press Enter for: `~/Code/opendatahub-test-plans/plans/`
   >
   > Note: Replace `<team-name>` with your team name (e.g., `ai-hub`, `dashboard`, etc.)

4. Empty/Enter uses the default or saved path; otherwise use the supplied path. Expand `~` to the home
   directory.

5. Unless `FORCE_OUTPUT_DIR=true`, validate the target against the skill repository:
   ```bash
   export CLAUDE_SKILL_DIR
   force_flag=$([ "$FORCE_OUTPUT_DIR" = "true" ] && echo "--force" || echo "")
   (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/repo.py validate-local-path "$target_dir" $force_flag) || exit 1
   ```

6. Unless `--output-dir` is used, ask whether to save the preference:
   > Save this location for future /test-plan-create runs? [yes/no]

   If **yes**, save to `.claude/settings.json`:
     ```bash
     mkdir -p .claude

     if [ -f .claude/settings.json ]; then
         jq '.["test-plan"].output_dir = "'"$target_dir"'"' .claude/settings.json > .claude/settings.json.tmp
         mv .claude/settings.json.tmp .claude/settings.json
     else
         echo '{"test-plan": {"output_dir": "'"$target_dir"'"}}' > .claude/settings.json
     fi

     echo "✓ Saved preference to .claude/settings.json"
     ```

   If **no**, continue without saving; ask again next time.

7. Create and enter the output directory:
   ```bash
   mkdir -p "$target_dir"
   cd "$target_dir"
   echo "✓ Creating test plan artifacts in: $target_dir"
   ```

8. `save-snapshot` (Step 1.5) persists the output directory to
   `<feature_dir>/.test-plan-output-dir.json` for discovery by other skills and scripts without
   environment variables.

### Step 1: Gather Information

1. **Strategy**: If a Jira key was provided, fetch it using the `fetch_issue.py` script. If auto-detected, read the local file from `artifacts/strat-tasks/` instead — do NOT fetch.

   **Fetching from Jira:**
   ```bash
   repo_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)
   tmp_result=$(cd "$repo_root" && uv run python scripts/parse_strat.py new-strat-tmp) || exit 1
   strategy_file=$(echo "$tmp_result" | jq -r '.strategy_file')
   (cd "$repo_root" && \
    uv run python scripts/fetch_issue.py <JIRA_KEY> --output "$strategy_file")
   ```

   **Auto-detected from `artifacts/strat-tasks/<JIRA_KEY>.md`** (shared cache; also a Jira-outage fallback for other skills):
   ```bash
   resolve_result=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/parse_strat.py resolve-local "<JIRA_KEY>") || exit 1
   strategy_file=$(echo "$resolve_result" | jq -r '.strategy_file')
   ```

   - `components` is extracted deterministically in Step 1.5 (`parse_strat.py save-snapshot`).
2. **ADR** (if provided): Read the ADR file for additional technical detail (API endpoints, data models, implementation specifics).

### Step 1.5: Parse Strategy Sections and Snapshot the Strategy

Run the STRAT parser on the fetched strategy file, before the snapshot step below moves/copies it:

```bash
repo_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)
gate_result=$(cd "$repo_root" && uv run python scripts/parse_strat.py workflow-inputs "$strategy_file")
gate_exit=$?

if [ "$gate_exit" -ne 0 ]; then
  echo "workflow-inputs failed to parse the strategy; cannot proceed" >&2
  echo "$gate_result" >&2
  exit 1
fi

gate_status=$(echo "$gate_result" | jq -r '.status')

if [ "$gate_status" = "ok" ]; then
  ac_json=$(echo "$gate_result" | jq -c '.ac_json')
  nfr_json=$(echo "$gate_result" | jq -c 'if .nfr_json.found then .nfr_json else empty end')
  oos_json=$(echo "$gate_result" | jq -c 'if .oos_json.found then .oos_json else empty end')
  ac_count=$(echo "$gate_result" | jq -r '.ac_count')
  nfr_category_flags=()
  while IFS= read -r cat; do [ -n "$cat" ] && nfr_category_flags+=(--nfr-category "$cat"); done < <(echo "$gate_result" | jq -r '.nfr_categories[]? // empty')
  strat_gaps=""
  [ -z "$nfr_json" ] && strat_gaps="${strat_gaps}- Strategy has no Non-Functional Requirements section.\n"
  [ -z "$oos_json" ] && strat_gaps="${strat_gaps}- Strategy has no Out-of-Scope section.\n"
fi

feature_name="<user-provided feature directory name from Inputs (Optional) if given, else snake_case derived from the strategy title>"
(cd "$repo_root" && uv run python scripts/validate.py feature-name "$feature_name") || exit 1
feature_dir="$(pwd)/$feature_name"
```

**Snapshot the strategy** at `$feature_dir/.source-strategy.md` — creates the feature dir, moves
temp fetches, copies (never deletes) the shared cache:

```bash
snapshot_result=$(cd "$repo_root" && uv run python scripts/parse_strat.py save-snapshot "$strategy_file" "$feature_dir") || exit 1
strategy_file=$(echo "$snapshot_result" | jq -r '.strategy_file')
components=$(echo "$snapshot_result" | jq -r '.components | join(",")')
```

**If `$gate_status` is `no_acceptance_criteria`** (no ACs found or count is 0), **STOP immediately**:
1. Write a lowest-score review:
   ```bash
   (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py set \
       <absolute_path_to_output_dir>/<feature_name>/TestPlanReview.md \
       feature="<feature_name>" source_key=<JIRA_KEY> score=0 pass=false verdict=Rework \
       scores='{"specificity":0,"grounding":0,"scope_fidelity":0,"actionability":0,"consistency":0}' \
       auto_revised=false)
   ```
2. Write review body: `"Strategy has no acceptance criteria. Cannot generate AC-traced test plan."`
3. Stamp `test-plan-rubric-fail` on the Jira issue (non-blocking). Do NOT proceed to Step 2.

### Step 2: Analyze (Parallel Sub-Agents)

**Scope and traceability**: Generate e2e/system and UI plans only; Section 2.1 excludes unit,
integration, and component levels. Every Section 1.3 objective must cite a grounded AC/NFR. Every
meaningful in-scope entry in Sections 1.2, 2.3, 7.1–7.5, and 8 must end with `(Objective: #N)`
linking it to a grounded objective; do not guess `N`. A Section 7.1–7.5 category with no concrete
AC/NFR grounding is **Not Applicable** and needs no marker. Step 3.2 validates this deterministically.

The endpoint analyzer owns disclosure of every in-scope Section 1.2 item it omits from Section 1.3
solely because it lacks a backing AC. Pass that analyzer output through unchanged and collect its
required `## Gaps` output into `TestPlanGaps.md` at Step 3.5. The parent must not be responsible for
adding a concise entry in the analyzer `## Gaps` material passed to Step 3.5, inventing an objective,
or using a free-text matcher to infer further exclusions.

Invoke the three forked analyzer skills **in parallel** using the Skill tool. Each runs in isolation
and reads supplied strategy/ADR paths. Pass `<feature_name>/.source-strategy.md` and any ADR as
paths, never inline; pass the Step 1.5 JSON extractions as ground truth and do not re-derive them.

- **`test-plan.analyze.endpoints`**: Pass strategy, ADR, `ac_json`, `oos_json`, and `nfr_json`.
  Produce scope, grounded-objective, and e2e-surface findings for Sections 1 and 4.
- **`test-plan.analyze.risks`**: Pass strategy, ADR, `ac_json`, and `nfr_json`. Produce e2e/UI
  levels, types, priorities, mitigated risks, and NFR assessments for Sections 2, 7, and 8.
- **`test-plan.analyze.infra`**: Pass strategy and ADR. Produce environment, data, user,
  infrastructure, and tooling findings for Section 3.

After all three return, merge their structured findings into the template (Step 3) and collect
their `## Gaps` sections for Step 3.5. Do not add information absent from every sub-agent output.

### Step 3: Generate Files

1. Ensure `test_cases/` exists: `mkdir -p -- "$feature_dir/test_cases"`
2. **Resolve the strategy browse URL** from the configured Jira URL; never hardcode or infer a host
   (the `JIRA_BASE_URL` fallback matches `require_env`):
   ```bash
   jira_url="${JIRA_URL:-$JIRA_BASE_URL}"
   strat_url="${jira_url%/}/browse/${JIRA_KEY}"
   ```
   Use this exact `strat_url` for `{strat_url}` in the template and the Jira strategy link in
   `README.md`.
3. Read the template from `${CLAUDE_SKILL_DIR}/test-plan-template.md` using the Read tool
4. Fill `<feature_name>/TestPlan.md` exactly to the template structure; do not add, remove, or
   reorder sections or write frontmatter manually (Step 3.1 handles it).
   - Wrap prose and list items to 100 characters; tables, code blocks, and headings are exempt.
   - Use proper `##`/`###`/`####` headings, never bold text; apply Step 2 markers without marking
     excluded Section 1.2 items. These rules apply to `TestPlan.md`, `TestPlanGaps.md`, and
     `README.md`.
5. In Section 9.2, fill Interface from Section 4 and leave Test Cases and Coverage empty for later.
6. Generate `README.md` with the feature name and one-line description, Jira strategy link using
   `strat_url`, ADR link if provided, TestPlan link, and where automated tests will be implemented.

### Step 3.1: Set Frontmatter

After generating `TestPlan.md`, set its frontmatter with `frontmatter.py` via Bash; this validates
metadata against the schema before writing.

**First, auto-detect source type from Jira key prefix:**
```bash
if [[ <JIRA_KEY> == RHAISTRAT-* ]]; then
    SOURCE_TYPE="strat"
elif [[ <JIRA_KEY> == RHOAIENG-* ]]; then
    SOURCE_TYPE="issue"
fi
```

**Then set frontmatter:**

**IMPORTANT**: Run Python scripts from the test-plan repo (where `pyproject.toml` is), not the output
directory; use absolute file paths.

```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py set <absolute_path_to_output_dir>/<feature_name>/TestPlan.md \
    feature="<feature_name>" \
    source_key=<JIRA_KEY> \
    source_type=$SOURCE_TYPE \
    status=Draft \
    author="<team_name>" \
    components="$components" \
    additional_docs="<comma-separated list of doc links, or []>")
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/version.py set <absolute_path_to_output_dir>/<feature_name>/TestPlan.md 1.0.0)
```

- `components` comes from Step 1.5; an empty string coerces to `[]`.
- `additional_docs` includes the ADR and other user-provided document links, or `[]` if none.
- The script sets `last_updated` to today's date and defaults `reviewers` to `[]`.

On error, fix the field values and retry; do not write frontmatter by hand.

### Step 3.2: Validate Generated Test Plan

After setting frontmatter, run the deterministic checks. Step 1.5's STOP gate guarantees the parsed
`$ac_count` and `$nfr_category_flags` are available:

```bash
testplan="<absolute_path_to_output_dir>/<feature_name>/TestPlan.md"
feature_dir="<absolute_path_to_output_dir>/<feature_name>"
repo_root=$(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel)

team_list=$(cd "$repo_root" && uv run python scripts/get_component_test_dir.py --teams-only "$feature_dir") || {
    echo "ERROR: scripts/get_component_test_dir.py --teams-only failed — stopping." >&2
    echo "$team_list" >&2
    exit 1
}

(cd "$repo_root" && \
 scope_result=$(uv run python scripts/validate_test_scope.py "$testplan" \
     --include-teams="$team_list" --checks-dir=scripts/checks) && \
 (echo "$scope_result" | jq -e '.valid' >/dev/null || { echo "$scope_result" >&2; exit 1; }) && \
 uv run python scripts/validate.py ac-citations "$testplan" --ac-count "$ac_count" "${nfr_category_flags[@]}" && \
 uv run python scripts/validate.py ac-coverage "$testplan" --ac-count "$ac_count" && \
 uv run python scripts/validate.py structure "$testplan" && \
 uv run python scripts/validate.py category-prefixes "$testplan" && \
 uv run python scripts/validate.py interface-types "$testplan" && \
 uv run python scripts/validate.py infra-scope "$testplan")

citation_inputs=$(cd "$repo_root" && uv run python scripts/build_citation_inputs.py "$feature_dir" \
    --strategy-file "$strategy_file") || {
    echo "ERROR: scripts/build_citation_inputs.py failed — stopping." >&2
    echo "$citation_inputs" >&2
    exit 1
}
echo "$citation_inputs" | jq -e '.scope_coverage_result.valid' >/dev/null || {
    echo "ERROR: scope coverage is incomplete; add `(Objective: #N)` markers and grounded objectives." >&2
    echo "$citation_inputs" >&2
    exit 1
}
```

If a check fails, fix `TestPlan.md` and re-run **once**; if it fails again, **STOP** and report it.

### Step 3.5: Collect Gaps and Prompt for Additional Documents

Write each Step 2 sub-agent's full raw analysis verbatim to
`<feature_dir>/.analysis-endpoints.md`, `<feature_dir>/.analysis-risks.md`, and
`<feature_dir>/.analysis-infra.md`; do not hand-slice `## Gaps` because the script extracts it.

Then run:

```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
 uv run python scripts/consolidate_gaps_and_stamp.py \
   --feature-name "<feature_name>" \
   --source-key <JIRA_KEY> \
   --source endpoints=<feature_dir>/.analysis-endpoints.md \
   --source risks=<feature_dir>/.analysis-risks.md \
   --source infra=<feature_dir>/.analysis-infra.md \
   --last-updated "$(date -u +%F)" \
   --skip-cleanup \
   --out <feature_dir>/TestPlanGaps.md)
```

Success writes `TestPlanGaps.md` (body plus frontmatter) and prints
`{"gap_count": int, "status": str, "next": "proceed"|"prompt_user"}`. Never hand-count gaps,
hand-edit frontmatter, or run `check-interactive`. If it exits non-zero, temp files remain for
debugging; fix the issue and re-run.

- **`next` is `proceed`:** skip the menu. Go to Step 3.6.
- **`next` is `prompt_user`:** present the menu below.

**Interactive gaps menu** (only when `next` is `prompt_user`): Present AskUserQuestion, list gaps
from `TestPlanGaps.md`, and offer:

1. **Provide documents** — paste file paths to resolve gaps
2. **Proceed to review** — continue as-is
3. **Proceed + generate test cases** — continue and auto-run `/test-plan-create-cases`

**If option 1:** Read the documents, re-run only the relevant Step 2 sub-agents, update the test
plan, then re-run the same `consolidate_gaps_and_stamp.py` command (including `--skip-cleanup`);
follow `next` from the new JSON.
**If option 2:** Proceed to Step 3.6.
**If option 3:** Proceed to Step 3.6, then automatically invoke `/test-plan-create-cases` with the
feature directory after Step 4.

### Step 3.6: Stamp Jira label — test plan created

Add `test-plan-auto-created` to the source Jira issue to mark the generated plan for org-pulse tracking.

Read `source_key` from `<feature_name>/TestPlan.md` frontmatter before stamping:
```bash
source_key=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py read <absolute_path_to_output_dir>/<feature_name>/TestPlan.md source_key)
```

Then add the label with `add_jira_labels.py`:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
 uv run python scripts/add_jira_labels.py "$source_key" test-plan-auto-created)
```

### Step 4: Review, Score, and Improve

After the gaps flow, invoke the internal **`test-plan.review`** skill with the feature directory. It
applies the 10-point rubric (Specificity, Grounding, Scope Fidelity, Actionability, Consistency;
0–2 each), may auto-revise internally for up to 2 cycles, and writes
`<feature_name>/TestPlanReview.md` with scores and feedback. Full criteria live in `test-plan.review`.

**Handle the review output:**

1. Read the verdict from `<feature_name>/TestPlanReview.md` frontmatter.
2. Apply only clearly correct reviewer improvements:
   - Consistency fixes (e.g., missing entries in Section 9.2 that are in Section 4)
   - Generic priority definitions that should be feature-specific (when the specific language is in the strategy)
   - **TBD grammar**: Never invent a resolution path. Retain a genuinely unknown required value only when the source supports an explicit resolution path in the form `TBD — Resolution: {concrete action} from/with/by/before/after/using {named source or timing}`; otherwise leave the gap documented in TestPlanGaps.md rather than claiming Actionability 2/2.
   - **Only add content that is directly traceable to the source documents** (strategy, ADR, API specs, design docs, or any additional_docs) — do not make assumptions about where documentation exists or what it contains.

   Use the Edit tool for applied auto-fixes.
3. Show the final score/verdict, auto-fixes, and remaining `TestPlanGaps.md` gaps.
4. For **Rework**, advise the user to provide source documents (ADR, API spec, or design doc) before
   generating test cases.

### Step 4.5: Stamp rubric verdict label

After reading the review verdict, stamp the corresponding label on the source Jira issue for org-pulse
review-outcome tracking.

**Determine which labels to add:**
- Verdict **"Ready"** → add label `test-plan-rubric-pass`
- Verdict **"Revise"** → add label `test-plan-rubric-revise`
- Verdict **"Rework"** → add label `test-plan-rubric-fail`
- Any other verdict value → log a warning and skip rubric label stamping

**Read frontmatter values explicitly before stamping:**
```bash
verdict=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py read <absolute_path_to_output_dir>/<feature_name>/TestPlanReview.md verdict)
auto_revised=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py read <absolute_path_to_output_dir>/<feature_name>/TestPlanReview.md auto_revised)
source_key=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py read <absolute_path_to_output_dir>/<feature_name>/TestPlan.md source_key)
```

**Build label list and apply:**
```bash
if [ "$auto_revised" = "true" ]; then
    (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
     uv run python scripts/add_jira_labels.py "$source_key" --verdict "$verdict" test-plan-auto-revised)
else
    (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && \
     uv run python scripts/add_jira_labels.py "$source_key" --verdict "$verdict")
fi
```

Shared label rule for Steps 3.6 and 4.5: label stamping is **non-blocking** — if it fails, log a
warning and continue; do not retry or halt the workflow.

### What this skill does NOT do

- **Sources and feedback:** Fetch only the requested strategy or issue; never fetch child stories. Read ADRs only from supplied local paths. ADR URLs are metadata only—never fetch them. Do not resolve GitHub PR review comments; use `/test-plan-resolve-feedback`.
- **Test-case artifacts and ownership:** Do not create individual `TC-*.md` files or executable tests. Section 5.2 is the allowed test-category/type contract. Leave Sections 5.1, 6, and 9.1 as placeholders. `/test-plan-create-cases` owns case files, Sections 5.1, 6.1–6.2, Section 9.1, and Section 9.2’s Test Cases column. This skill fills only Section 9.2’s Interface column; downstream coverage tooling fills Coverage; this skill owns Section 9.3’s change log.
- **Scope and traceability:** Section 2.1 allows only e2e/system and UI levels. Section 1.3 must cover every AC and grounded NFR with valid `(AC: #N)` or `(NFR: category)` citations; never invent objectives or scope.
- **Analysis:** Sections 7 and 8 must remain source-grounded in the strategy/ADR; do not invent unsupported NFR analysis, risks, or mitigations.

$ARGUMENTS
