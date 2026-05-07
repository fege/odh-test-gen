# test-plan.ui-verify — Implementation Guide

---

## Start

```bash
python3 <SKILL_DIR>/scripts/ui_read_ctx.py
```

Write down every `KEY=value` line printed. Then use the `Read` tool on `<SKILL_DIR>/.tmp/ui_context.json` to get the full `test_cases` array. Do not write inline Python.

Also use the `Read` tool to read `<SKILL_DIR>/js-patterns.md` — it contains the JS assertion templates referenced in Phase 2D.

---

## Phase 2: Execute Test Cases

For each TC in `ctx["test_cases"]`:

### 2A — Preconditions

Every TC starts with a clean, independent state — always evaluate its preconditions from scratch, never assume them from earlier TCs. If a precondition in `tc["preconditions"]` is verifiably not met, block and skip. For cluster-state preconditions that cannot be checked in the browser (e.g. "upgrade completed", "route exists"), use `oc` to verify — checking whether a route or resource exists is always sufficient to confirm or deny an upgrade/deployment precondition:

```bash
python3 <SKILL_DIR>/scripts/ui_block.py --tc <TC_ID> --title "<TC title from ctx>" \
  --reason "Precondition not met: <text>" --what "Precondition check"
```

### 2B — Reset

Always run both navigations before every TC, even when already on the correct page. This is what clears filters, search terms, and other React state left by the previous TC.

```bash
python3 <SKILL_DIR>/scripts/ui_interact.py goto <TARGET_URL>
python3 <SKILL_DIR>/scripts/ui_interact.py goto <TARGET_URL><matched_path_from_KNOWN_ROUTES>
```

Use `KNOWN_ROUTES` to find the correct path. Only fall back to inspecting nav links if `goto` returns exit 2 for every known candidate.

### 2C — Execute steps

```bash
python3 <SKILL_DIR>/scripts/ui_interact.py click "<description>"
python3 <SKILL_DIR>/scripts/ui_interact.py fill "<description>" "<value>"
python3 <SKILL_DIR>/scripts/ui_interact.py scroll bottom
python3 <SKILL_DIR>/scripts/ui_interact.py goto "<url>"
python3 <SKILL_DIR>/scripts/ui_interact.py expand
python3 <SKILL_DIR>/scripts/ui_interact.py wait [ms]
```

Complete all TC steps before asserting any Expected Result.

**`--in-row <text>`**: when a page has multiple rows each containing the same button or link (e.g. a table where every row has an action button with the same label), use `--in-row` to scope the click to the row that contains the given text — avoiding clicking the first match when you need a specific row.

**`click` not-found semantics:** Exit 1 means the target was absent, printed as `~ click: '...' — not found`. It is not an error; the caller decides whether absence is acceptable. Use this to exhaust pagination: call `click "Load more"` in a loop until exit 1.

**`expand`** — two modes:

```bash
# Mode 1 — no selector: exhausts pagination only.
# Scrolls to bottom and clicks "Load more" / "View more" / "Load all" buttons
# repeatedly until none remain. Does NOT click "+N more" or bare "Show more" —
# those are inline overflow toggles (filter panels, card labels) not pagination,
# and counting them as pages would cause undercounting of actual results.
python3 <SKILL_DIR>/scripts/ui_interact.py expand

# Mode 2 — with selector: clicks ALL disclosure buttons inside matched containers.
# Covers any overflow text (+N more, Show more, View more, Expand…) scoped to
# the container. Cannot touch tab navigation or controls outside it.
python3 <SKILL_DIR>/scripts/ui_interact.py expand "<css-selector>"
```

Examples:
- `expand` — exhaust pagination after applying a filter (scroll + click until no more pages)
- `expand "[data-testid='<item-testid>']"` — reveal hidden labels/tags inside every item card
- `expand "[data-testid='<section-testid>']"` — expand a specific collapsible section

### 2D — Assert

One `ui_assert.py` call per Expected Result. No more, no fewer.

```bash
python3 <SKILL_DIR>/scripts/ui_assert.py \
  --tc <TC_ID> \
  --title "<TC title from ctx>" \
  --what "<Expected Result text>" \
  --expected "<expected outcome>" \
  --js "<JS returning PASS:detail or FAIL:reason>" \
  --screenshot verify-<short-description>
```

Always highlight the verified element inside `--js` by setting `el.style.outline='3px solid green'` (PASS) or `'3px solid red'` (FAIL) on the found element before returning the verdict. This records what was actually checked in the screenshot without closing open overlays — a style change on an existing element does not trigger mutation observers. The outline is automatically removed by the cleanup step. Only use `--selector` for static page elements where a pointer label is also wanted.

Always pass `--title` using `tc["title"]` from the context — it is stored in the report log so that `report.html` shows real TC names instead of just IDs.

**For ephemeral UI state** (dropdowns, menus, accordions that close between tool calls), use `--click-before` to open the container and assert its contents in one atomic call. Always pair it with `--retry 1` — if the container was already open and the click toggled it closed, the retry re-clicks to reopen it. Never open with a separate `ui_interact.py click` and assert in the next call — the container will be closed by then:

```bash
python3 <SKILL_DIR>/scripts/ui_assert.py \
  --tc <TC_ID> \
  --title "<TC title from ctx>" \
  --click-before "Application launcher" \
  --retry 1 \
  --what "<Expected Result text>" \
  --expected "<expected outcome>" \
  --js "<JS that reads content from the now-open container>" \
  --screenshot verify-<short-description>
```

**To guard against wrong-page assertions** (wrong tab, unexpected redirect), pass a stable substring of the expected URL. The assertion aborts with WRONG_PAGE (exit 2) before the JS runs if the URL does not match:

```bash
python3 <SKILL_DIR>/scripts/ui_assert.py --tc <TC_ID> --title "..." \
  --expected-url-contains "rh-ai.apps" \
  --what "..." --expected "..." --js "() => ..." --screenshot verify-<desc>
```

**For async-updating UI** (counters, status fields, charts that update after an action), use `--retry N` to retry the JS up to N times with 500 ms between attempts before logging FAIL:

```bash
python3 <SKILL_DIR>/scripts/ui_assert.py --tc <TC_ID> --title "..." \
  --retry 2 \
  --what "..." --expected "..." --js "() => ..." --screenshot verify-<desc>
```

**When the expected value depends on the environment** (URL hostname, resource ID, cluster-specific name), always run `--inspect` first to read the actual current value, then write the assertion from what you observe. Never assume a value from a TC description — names used in TCs (route names, service names, pattern labels) often do not appear literally in the running system's URLs or DOM.

**When checking an element's attribute** (href, text, state), always find the element first and then read its value — never search for elements that already contain the target value. An element exists regardless of what value it currently holds; searching only for the new value misses the case where it exists with the old value and produces a misleading "not found" failure. See `js-patterns.md` for the correct pattern.

**When correcting a FAIL by rewriting the JS**, always add `--replace` so the first attempt does not stay in the log alongside the corrected one. The duplicate assertion warning is the signal: act on it immediately with `--replace`.

**If the assertion FAILs because page state was not ready** (e.g. a section needed expanding first), fix the state via `ui_interact.py`, then re-assert with `--replace` to remove the ghost FAIL:

```bash
python3 <SKILL_DIR>/scripts/ui_assert.py --tc <TC_ID> --what "<same text>" ... --replace
```

**If the assertion FAILs and you need to diagnose why**, run one `--inspect` call (not logged, not scored), then re-assert or log the FAIL and move on:

```bash
python3 <SKILL_DIR>/scripts/ui_assert.py --tc <TC_ID> --inspect \
  --what "diagnostic" --expected "" \
  --js "() => { return 'PASS:' + ...; }" \
  --screenshot inspect-<description>
```

**If a step cannot be executed at all** (requires backend access, cluster admin, missing data that cannot be created from browser):

```bash
python3 <SKILL_DIR>/scripts/ui_block.py --tc <TC_ID> --title "<TC title from ctx>" \
  --reason "<reason>" --what "<what>"
```

If the Expected Result *can* be tested from the browser — even partially — assert it and let it PASS or FAIL. BLOCK only when there is no browser action that could produce the needed data.

#### JS patterns

See `<SKILL_DIR>/js-patterns.md` (already read at Start) for all assertion templates: counting, visibility, active state, exclusion, filter composition, and screenshot naming rules.

### 2E — End TC

On crash or browser disconnect: `ui_block.py --incomplete`. Never abandon a TC without logging.

---

## Phase 3: Stop browser

```bash
python3 <SKILL_DIR>/scripts/ui_stop_browser.py
```

## Phase 4: Cleanup

```bash
python3 <SKILL_DIR>/scripts/ui_cleanup.py
```

## Phase 5: Collect

```bash
python3 <SKILL_DIR>/scripts/ui_collect.py
```

Record the printed `SESSION_DIR=<path>` — use it in Phase 6.

## Phase 6: Report

```bash
python3 <SKILL_DIR>/scripts/ui_report.py <SESSION_DIR>
```

This generates two files inside `<SESSION_DIR>`:
- `report.html` — visual report with color-coded verdicts, TC details, and screenshot thumbnails
- `report.md` — plain-text summary (same content, Markdown format)

After generation, print the Markdown report for the user:

```python
from pathlib import Path
print(Path("<SESSION_DIR>/report.md").read_text())
```

Then tell the user they can open `report.html` in a browser for the full visual report with screenshots:

```
Open the visual report: open <SESSION_DIR>/report.html
```

**Upgrade runs:** if `ctx["upgrade_phase"]` is `"pre"`, remind the user to upgrade the cluster then re-run with `--upgrade-phase post --baseline <SESSION_DIR>` where `<SESSION_DIR>` is the session path printed by `ui_collect.py` in Phase 5. Always include `--baseline` explicitly — the auto-detected pointer file is deleted by collect and will not be available for the post run. If `ctx["upgrade_phase"]` is `"post"` and `ctx["upgrade_baseline_dir"]` is set, `ui_report.py` also generates `upgrade-report.html` — print its path and tell the user to open it for the FIXED / REGRESSION / STABLE / STILL FAILING comparison.

---

## Safety Rules

1. Never declare PASS without an explicit logged assertion
2. Never hardcode absolute paths — use `ctx["skill_dir"]` or import from `paths.py`
3. Never write inline Python temp scripts — use the bundled scripts for everything
4. Never print credentials
5. Always run Phase 4 cleanup, even on failure
6. Max 2 retries for the same action before calling `ui_block.py --incomplete`
7. If 3 consecutive tool calls produce no progress, call `ui_block.py --incomplete` and move on
8. Route discovery is unlimited — try all `KNOWN_ROUTES` candidates before giving up
9. One TC at a time — always log before moving to the next TC
