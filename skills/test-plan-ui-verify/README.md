# test-plan.ui-verify

Verifies UI test cases against a live ODH/RHOAI cluster. Loads TCs from a GitHub PR or repo folder, runs browser interactions via a persistent Playwright CDP browser, and produces a visual HTML report with per-TC PASS/FAIL/BLOCKED/INCOMPLETE verdicts and screenshots.

Test cases with no UI steps are automatically marked BLOCKED; they are not skipped.

## Prerequisites

| Requirement | Install |
|-------------|---------|
| Python 3.11+ | `brew install python` or system package manager |
| Playwright | `pip install playwright && playwright install chromium` |
| pyyaml | `pip install pyyaml` (or `pip install -r requirements.txt`) |
| GitHub CLI | `brew install gh && gh auth login` |
| Live ODH/RHOAI cluster | Access to `oc login` or credentials in `test-variables.yml` |

## Setup

### 1. Credentials

Copy the template and fill in your cluster details:

```bash
cp skills/test-plan-ui-verify/test-variables.yml.example \
   skills/test-plan-ui-verify/test-variables.yml
```

Edit `test-variables.yml`:

```yaml
target_url: "https://rh-ai.apps.my-cluster.example.com"   # dashboard URL
idp: "ldap-provider-qe"                                    # IDP name on login page
admin_user:
  username: "ldap-admin1"
  password: "your-password-here"
```

`test-variables.yml` is gitignored — it will never be committed.

### 2. First-time check

```bash
python3 skills/test-plan-ui-verify/scripts/ui_prepare.py --setup
```

Prints detected cluster API, username, and the exact fields to fill in.

## Usage

### Step 1 — terminal: run setup

```bash
python3 skills/test-plan-ui-verify/scripts/ui_prepare.py \
  --test-plan-pr https://github.com/fege/test-plan/pull/5
```

This loads test cases, validates credentials, launches a headless Chromium browser, logs in, and writes a context file. Claude Code is launched automatically at the end.

### Step 2 — Claude Code: run verification

```
/test-plan-ui-verify
```

Claude reads the context, executes each TC via the browser, logs assertions, and writes the report.

> If Claude Code does not open automatically at the end of Step 1, start it manually in the repo root and type `/test-plan-ui-verify`.

### Flags

| Flag | Description |
|------|-------------|
| `--test-plan-pr <url>` | Load TCs from any open GitHub PR (e.g. `https://github.com/org/repo/pull/5`) |
| `--test-plan <path>` | Load TCs from a folder in main (e.g. `org/repo/feature_folder`) |
| `--tc <filter>` | Exact TC ID (`TC-FILTER-001`) or category prefix (`TC-FILTER`, `TC-E2E,TC-CARD`) |
| `--priority <P>` | Filter by priority: `P0`, `P1`, or `P2`. Default: all |
| `--target-url <url>` | Override dashboard URL (skips auto-detection from `test-variables.yml`) |
| `--refresh-map <path>` | Regenerate `element-map.yaml` from an odh-dashboard source checkout |
| `--setup` | Print cluster API and credential field guide, then exit |
| `--upgrade-phase <pre\|post>` | Upgrade testing: `pre` captures a baseline on the old cluster; `post` runs on the new cluster and generates a comparison report |
| `--baseline <session-dir>` | Explicit baseline for `--upgrade-phase post`; auto-selected from baseline if omitted |

### Examples

```bash
# Run all TCs from a PR
python3 scripts/ui_prepare.py --test-plan-pr https://github.com/fege/test-plan/pull/5

# Run only P0 TCs
python3 scripts/ui_prepare.py --test-plan-pr <url> --priority P0

# Run a specific TC
python3 scripts/ui_prepare.py --test-plan-pr <url> --tc TC-FILTER-001

# Run a category of TCs
python3 scripts/ui_prepare.py --test-plan-pr <url> --tc TC-FILTER

# Run against a specific cluster URL
python3 scripts/ui_prepare.py --test-plan-pr <url> --target-url https://rh-ai.apps.other-cluster.example.com

# Upgrade testing — pre-upgrade baseline
python3 scripts/ui_prepare.py --test-plan-pr <url> --upgrade-phase pre

# Upgrade testing — post-upgrade comparison (TCs auto-selected from baseline)
python3 scripts/ui_prepare.py --test-plan-pr <url> --upgrade-phase post --baseline results/<pre-session>
```

## Output

Results land in `skills/test-plan-ui-verify/results/<session>/`:

| File | Description |
|------|-------------|
| `report.html` | Visual report — filter by verdict/priority, click overview rows to jump to TCs, inline screenshot thumbnails with lightbox; open with `open results/<session>/report.html` |
| `report.md` | Plain-text Markdown summary with embedded screenshot links; for GitHub comments or terminal review |
| `tc_log.json` | Raw assertion data (what, expected, result, detail per check) |
| `TC-*-verify-*.png` | Highlighted screenshot for each logged assertion |
| `upgrade-report.html` | *(upgrade post-runs only)* Side-by-side comparison: FIXED / REGRESSION / STABLE per TC; links to pre and post individual reports |
| `pre-session/` | *(upgrade post-runs only)* Symlink to the baseline session — navigate to `pre-session/report.html` for the pre-upgrade results |

### Sample report

```markdown
# test-plan.ui-verify — tool_calling_model_catalog

**Overall: ❌ FAIL**

| | |
|---|---|
| **Date** | 2026-04-22 15:04 |
| **Source** | PR #5 |
| **Strategy** | RHAISTRAT-1262 |
| **Target** | https://rh-ai.apps.my-cluster.example.com |

## Summary

| Verdict | Count |
|---------|------:|
| ✅ PASS | 2 |
| ❌ FAIL | 1 |
| ⚠️ BLOCKED | 0 |
| 🔴 INCOMPLETE | 0 |

## Results

### ❌ FAIL  `TC-FILTER-001` `P0` — 'Tool Calling' task filter visible in left navigation

> Verify that the 'Tool Calling' task filter appears in the left navigation sidebar.

| Checked | Expected | Result | Detail |
|---------|----------|--------|--------|
| Filter visible and selectable | Filter link present | ✅ PASS | Found under "Show more" expansion |
| Label clearly readable | Distinct label | ✅ PASS | Distinct from neighboring filters |
| Filter shows model count badge | Badge visible | ❌ FAIL | No count badge exists on any task filter |

![TC-FILTER-001-verify-badge.png](./TC-FILTER-001-verify-badge.png)

---

## Failure Analysis

| TC | Verdict | Root Cause |
|----|---------|------------|
| `TC-FILTER-001` | ❌ FAIL | No count badge exists on any task filter |
```

## Supporting files

| File | Purpose |
|------|---------|
| `test-variables.yml` | Your cluster credentials — gitignored, copy from `.example` |
| `test-variables.yml.example` | Template with all supported fields |
| `component-registry.yaml` | ODH component → 50+ verified route paths and auth config |
| `element-map.yaml` | 1300+ `data-testid` selectors extracted from odh-dashboard source |
| `scripts/ui_prepare.py` | Setup: TC loading, credential resolution, browser launch, context file |
| `scripts/ui_interact.py` | Browser interaction: `click`, `fill`, `goto`, `scroll`, `expand`, `wait` (auto-relogins on session expiry) |
| `scripts/ui_assert.py` | Assertion runner: banner overlay, screenshot, TC log update |
| `scripts/ui_block.py` | Logs BLOCKED/INCOMPLETE entries to the TC log |
| `scripts/ui_report.py` | Generates `report.html` (visual, with screenshots) and `report.md` |
| `scripts/github_utils.py` | GitHub API helpers: fetch TC files and metadata via `gh` |
| `scripts/build_element_map.py` | Regenerates `element-map.yaml` from an odh-dashboard source checkout |

## How it works

```
ui_prepare.py
  ├── Loads TC-*.md from the PR via gh API
  ├── Resolves target URL (test-variables.yml → oc route → prompt)
  ├── Resolves cluster API (test-variables.yml → derived from URL → oc config)
  ├── Validates credentials via oc login
  ├── Snapshots existing cluster projects (for cleanup)
  ├── Launches headless Chromium with --remote-debugging-port
  ├── Logs in via OAuth (IDP click → username/password → redirect)
  └── Writes .tmp/ui_context.json + launches Claude Code

Claude (/test-plan-ui-verify)
  ├── Reads ui_context.json (target URL, known routes, TCs, browser CDP endpoint)
  ├── For each TC:
  │   ├── Checks preconditions → BLOCK if unmet
  │   ├── Navigates via known_routes lookup (no URL guessing)
  │   ├── Executes TC steps via ui_interact.py
  │   ├── Asserts each Expected Result via ui_assert.py (logged + screenshot)
  │   └── Marks PASS / FAIL / BLOCKED in ui_tc_log.json
  ├── Stops browser, runs cluster cleanup
  ├── Collects results into results/<session>/
  └── Generates report.html + report.md via ui_report.py
```

## Upgrade testing

Verify that a cluster upgrade didn't break UI behavior, then confirm a fix restored it.

### Setup: configure both clusters in `test-variables.yml`

```yaml
target_url: "https://rh-ai.apps.post-cluster.example.com"  # default
idp: "ldap-provider-qe"
admin_user:
  username: "admin"
  password: "your-password"
insecure_tls: true   # set if either cluster has an untrusted cert

upgrade_clusters:
  pre:
    target_url: "https://rhods-dashboard.apps.pre-cluster.example.com"
  post:
    target_url: "https://rh-ai.apps.post-cluster.example.com"
```

Only `target_url` needs to differ per cluster — `idp`, `admin_user`, and `cluster_api` (auto-derived) are shared.

### Workflow

```bash
# Phase 1 — old cluster: capture baseline
python3 scripts/ui_prepare.py --test-plan-pr <url> --upgrade-phase pre

# [upgrade the cluster]

# Phase 2 — new cluster: compare against baseline (TCs auto-selected)
python3 scripts/ui_prepare.py --test-plan-pr <url> \
  --upgrade-phase post \
  --baseline results/<pre-session>
# → generates upgrade-report.html: FIXED / REGRESSION / STABLE / STILL FAILING

# Phase 3 — after a fix is applied: compare against same baseline
python3 scripts/ui_prepare.py --test-plan-pr <url> \
  --upgrade-phase post \
  --baseline results/<pre-session>   # same baseline as phase 2
# → upgrade-report.html now shows FIXED where phase 2 showed REGRESSION
```

The post-session directory contains a `pre-session/` symlink to the baseline so both reports are reachable from one folder. `upgrade-report.html` includes direct links to both individual reports.

**Note:** Resources created for upgrade testing are not auto-cleaned — they must persist through the upgrade cycle. Phase 6 will prompt you before proceeding and remind you to clean up manually when done.

## Troubleshooting

**Login fails:** Check `idp` in `test-variables.yml` matches the button label on the OpenShift login page exactly (case-sensitive). Run `--setup` to see the detected value.

**Route returns 404:** The cluster may be on an older dashboard version. `ui_prepare.py` writes all known routes to the context — Claude will try alternatives automatically.

**Browser not found:** Run `playwright install chromium` and ensure the `playwright` Python package is installed (`pip install playwright`).

**Session expires mid-run:** `ui_interact.py goto` detects OAuth redirects and re-authenticates automatically using `test-variables.yml` credentials. No manual intervention needed.

**`gh` authentication error:** Run `gh auth login` and ensure you have read access to the test-plan repository.
