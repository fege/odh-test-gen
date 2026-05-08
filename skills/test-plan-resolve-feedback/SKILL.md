---
name: test-plan-resolve-feedback
description: Assess PR review comments on a published test plan, let the user decide what to apply, make changes, and push updates to the same branch. Use after receiving PR review feedback to efficiently apply approved changes with human control over what gets updated.
argument-hint: <PR_URL>
user-invocable: true
model: sonnet
allowedTools:
  - Read
  - Edit
  - Bash
  - AskUserQuestion
---

# Test Plan Feedback Resolver

Read review comments from a GitHub PR, assess each one against the existing test plan, let the user decide which to apply, make the changes, and push updates to the same branch.

## Usage

```
/test-plan-resolve-feedback <PR_URL>
```

Examples:
- `/test-plan-resolve-feedback https://github.com/org/test-plans-repo/pull/42`

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **First argument** (required): Full GitHub PR URL (e.g., `https://github.com/<owner>/<repo>/pull/<number>`)

Parse the URL to extract `owner`, `repo`, and `PR_NUMBER`.

### Interactive fallback
If no PR URL is provided, ask the user for it via AskUserQuestion.

## Process

### Step 0: Pre-flight Checks

#### 0.0 Python dependencies

Install the test-plan package (makes all scripts importable):
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv sync --extra dev)
```

If installation fails, inform the user and do NOT proceed. Once installed, all Python scripts will work from any directory.

#### 0.1 GitHub CLI
Run `gh auth status` via Bash. If it fails, inform the user that `gh` CLI must be installed and authenticated. Do NOT proceed until this succeeds.

#### 0.2 Validate PR exists
Fetch PR metadata:
```bash
gh pr view <PR_NUMBER> --repo <owner>/<repo> --json number,title,state,headRefName,body
```
If the PR does not exist or is closed/merged, inform the user and stop.

#### 0.3 Locate or clone the repo

Parse repo name from `<owner>/<repo>`.

**Check if repo exists locally**:
```bash
repo_path=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/repo.py find "<repo_name>")
```

If found (exit code 0, prints path):
```bash
cd "$repo_path"
current_branch=$(git branch --show-current)

if [ "$current_branch" = "<head_branch>" ]; then
    # Already on the PR branch, just pull latest
    git pull origin <head_branch>
else
    # Need to switch to PR branch
    git fetch origin
    git checkout <head_branch> 2>/dev/null || git checkout -b <head_branch> origin/<head_branch>
    git pull origin <head_branch>
fi
```
- Set `repo_path` to the output
- Log: "✓ Using local clone: $repo_path (updated)"

If NOT found (exit code 1, empty output):
- Clone the repo:
  ```bash
  repo_path=$(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/repo.py clone "<repo_url>" "~/Code/<repo_name>")
  ```
- Checkout PR branch:
  ```bash
  cd "$repo_path"
  git checkout <head_branch>
  ```
- Set `repo_path` to `~/Code/<repo_name>`
- Log: "✓ Cloned to ~/Code/<repo_name>"

#### 0.5 Locate feature directory
Find the feature directory by looking for `TestPlan.md` on the branch:
```bash
find . -name "TestPlan.md" -not -path "./.claude/*"
```
If multiple feature directories are found, ask the user which one to use via AskUserQuestion.

#### 0.6 Validate frontmatter
Validate the TestPlan.md frontmatter. If validation fails, show the errors — these will need to be fixed as part of the feedback resolution.
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py validate <feature_dir>/TestPlan.md)
```

### Step 1: Collect Review Comments

1. Fetch conversation comments and formal reviews in one call:
   ```bash
   gh pr view <PR_NUMBER> --repo <owner>/<repo> --json comments,reviews
   ```

2. Fetch inline review comments (comments on specific lines/files):
   ```bash
   gh api repos/<owner>/<repo>/pulls/<PR_NUMBER>/comments
   ```

3. Parse and build a list of all comments with:
   - **Who**: reviewer username
   - **Where**: general, or specific file + line
   - **What**: the comment body

4. Filter out:
   - Bot comments
   - Purely conversational comments (e.g., "looks good", "thanks", "LGTM")
   - Already-resolved review threads (if resolution status is available)

If no actionable comments remain, inform the user and stop.

### Step 2: Read the Test Plan

Read `<feature_dir>/TestPlan.md` using the Read tool. This is needed to assess each comment against what the plan currently says.

If `TestPlanGaps.md` exists, read it too — some feedback may relate to known gaps.

### Step 3: Assess and Present Feedback

For each actionable comment, **assess it** against the existing test plan content and present your assessment to the user. Process comments one at a time (or in small related groups) via AskUserQuestion.

For each comment, present:

> **Feedback #<N>** — @<reviewer>
> **File**: <file> (line <line>, if inline)
>
> > <quoted reviewer comment>
>
> **Assessment**: <your analysis>
>
> Explain whether the feedback:
> - **Aligns** with the strategy and test plan — the reviewer is pointing out a genuine gap or issue
> - **Conflicts** with existing content — the reviewer may be suggesting something that contradicts the strategy scope or is explicitly out-of-scope
> - **Needs clarification** — the comment is ambiguous and you cannot determine the right change without more context
> - **Is already covered** — what the reviewer is asking for already exists in the plan (point to the specific section)
>
> If the feedback aligns, describe the **concrete change** you would make (which file, which section, what edit).
>
> **Action?**
> 1. **Apply** — make the suggested change
> 2. **Skip** — do not apply this feedback
> 3. **Discuss** — you want to provide more context before deciding

If the user chooses **Discuss**, engage in conversation about the feedback item, then re-present the action choice.

Keep a running tally of applied vs skipped items.

### Step 4: Apply Accepted Changes

For each accepted feedback item, apply the change:

- Use the Edit tool to modify `TestPlan.md`, `TestPlanGaps.md`, or `test_cases/TC-*.md`
- For frontmatter changes, ensure validation:
  ```bash
  (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py set <feature_dir>/TestPlan.md <field>=<value>)
  ```
- If a change affects test cases:
  - Update existing `TC-*.md` files as needed
  - **Regenerate `test_cases/INDEX.md` atomically** if test cases were added, removed, or re-prioritized:
    - Scan all TC-*.md files in test_cases/
    - Extract test_case_id, priority, title from each
    - Build complete INDEX.md with stats, category tables, links
    - Write entire file in one operation (do NOT append incrementally)
  - Update TestPlan.md Sections 5 and 8 to reflect changes

### Step 5: Update Frontmatter

After all changes are applied:

1. Bump the `version` patch number (e.g., `1.0.0` → `1.0.1`):
   ```bash
   (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py set <feature_dir>/TestPlan.md version="<new_version>")
   ```

2. Keep `status` as `In Review`

3. If gaps were resolved by the feedback, update `TestPlanGaps.md`:
   ```bash
   (cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py set <feature_dir>/TestPlanGaps.md gap_count=<new_count>)
   ```
   If all gaps resolved, set `status=Resolved`.

### Step 6: Validate

Run validation on all modified artifacts:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/frontmatter.py validate <feature_dir>/TestPlan.md)
```

If test cases were modified:
```bash
(cd $(git -C ${CLAUDE_SKILL_DIR} rev-parse --show-toplevel) && uv run python scripts/validate_test_cases.py <feature_dir> test-case)
```

If any validation fails, fix the issue before proceeding.

### Step 7: Commit and Push

1. Present the final summary of changes to the user via AskUserQuestion before committing:
   > **Ready to push changes**
   >
   > - **Applied**: <N> of <total> feedback items
   > - **Skipped**: <M> items
   > - **Version**: `<old_version>` → `<new_version>`
   > - **Files modified**:
   >   - <list of changed files>
   >
   > Push to branch `<head_branch>`? (yes/no)

   If the user declines, leave the changes uncommitted and stop.

2. Stage artifact changes selectively (exclude temp files):
   ```bash
   git add <feature_dir>/TestPlan.md \
           <feature_dir>/test_cases/*.md \
           <feature_dir>/TestPlanGaps.md
   # Explicitly excludes: .review-state.json and other temp files
   ```

3. Commit with a descriptive message that summarizes the actual changes applied, not just "resolve feedback". Use a heredoc to avoid shell injection from frontmatter values:
   ```bash
   git commit -m "$(cat <<'EOF'
   test-plan(<source_key>): <short summary of changes> (PR #<PR_NUMBER>)
   EOF
   )"
   ```
   Examples:
   - `test-plan(RHAISTRAT-400): add rollback test coverage, fix P0 priority definitions (PR #5)`
   - `test-plan(RHAISTRAT-1262): clarify scope boundaries, add missing DB endpoints (PR #12)`
   - `test-plan(RHAISTRAT-400): rewrite risk section per reviewer feedback (PR #5)`

   Generate the summary from the list of applied feedback items. Keep it concise — highlight the 2-3 most significant changes.

4. Push to the same branch:
   ```bash
   git push origin <head_branch>
   ```

### Step 8: Confirm

1. Display a summary:
   > **Feedback resolved successfully**
   >
   > - **PR**: #<PR_NUMBER>
   > - **Branch**: `<head_branch>`
   > - **Version**: `<old_version>` → `<new_version>`
   > - **Applied**: <N> feedback items
   > - **Skipped**: <M> feedback items
   >
   > The PR has been updated. Reviewers will be notified of the new commits.

2. Switch back to the previous branch:
   ```bash
   git checkout -
   ```

### What this skill does NOT do

- Does NOT create the initial test plan — use `/test-plan-create` for that
- Does NOT create the PR — use `/test-plan-publish` for that
- Does NOT re-run sub-agent analyzers — if feedback requires deeper re-analysis with new source documents, use `/test-plan-update` (planned)
- Does NOT change the PR title, description, or reviewers
- Does NOT blindly apply all feedback — every item is assessed and presented to the user for decision

$ARGUMENTS
