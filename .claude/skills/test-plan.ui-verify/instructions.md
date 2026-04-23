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

If a precondition in `tc["preconditions"]` is verifiably not met, block and skip:

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

Always pass `--title` using `tc["title"]` from the context — it is stored in the report log so that `report.html` shows real TC names instead of just IDs.

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
