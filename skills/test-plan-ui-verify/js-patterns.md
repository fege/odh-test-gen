# JS Assertion Patterns — test-plan.ui-verify

Reference for writing the `--js` argument to `ui_assert.py`. Every pattern returns a string starting with `PASS:` or `FAIL:` followed by a detail message.

---

## Counting

Two methods only. Count exactly what the ER asks about.

```js
// Method 1 — page's own result count (preferred when available).
// Matches a standalone number+unit at the start of a line. Works regardless
// of pagination, virtualisation, or how many DOM nodes are loaded.
// Only use when the page explicitly displays a count (e.g. "12 models").
"() => { const main=document.querySelector('main,[role=main],[data-testid=dashboard-page-main]')||document.body; const m=main.innerText.match(/^(\\d+)\\s+<unit>s?/im); return m?'PASS:'+m[1]:'FAIL:count indicator not found'; }"

// Method 2 — count visible DOM elements by data-testid (fallback).
// Exhaust pagination first. Use getBoundingClientRect (width>0 OR height>0):
// offsetParent returns null inside CSS grid/flex even for fully visible elements.
"() => { const n=[...document.querySelectorAll('[data-testid=\"<item-testid>\"]')].filter(e=>e.getBoundingClientRect().width>0||e.getBoundingClientRect().height>0).length; return n>0?'PASS:'+n:'FAIL:0 visible'; }"

// Method 2 with deduplication (when duplicate DOM nodes are suspected):
"() => { const names=new Set([...document.querySelectorAll('[data-testid=\"<item-testid>\"]')].filter(e=>e.getBoundingClientRect().width>0||e.getBoundingClientRect().height>0).map(e=>e.querySelector('[data-testid=\"<name-testid>\"]')?.textContent?.trim()||e.dataset.id||'')); return names.size>0?'PASS:'+names.size:'FAIL:0 unique'; }"
```

If both methods fail, return `FAIL:count not verifiable` and move to the next ER.

---

## Visibility

```js
// Element is visible (exists AND rendered — use for UI state checks):
"() => { const el=document.querySelector('[data-testid=\"<id>\"]'); const r=el?.getBoundingClientRect(); return el&&(r.width>0||r.height>0)?'PASS:visible':'FAIL:'+(el?'hidden':'not found'); }"

// Item has a property/label — query full subtree WITHOUT visibility filter.
// Overflow items (+N more) are NOT in DOM until expanded; expand first if needed.
"() => { const item=document.querySelector('<item-sel>'); return item?.querySelector('<prop-sel>')?'PASS:found':'FAIL:not found'; }"
```

---

## Active / applied state

Body text always contains option panels regardless of whether an option is applied. Check the specific indicator that only appears when the option is active.

```js
// Checkbox or toggle is checked:
"() => { const el=document.querySelector('[data-testid=\"<id>\"]'); return el?.checked||el?.getAttribute('aria-checked')==='true'?'PASS:checked':'FAIL:unchecked'; }"

// Item appears in an applied-state zone (chip bar, badge area, etc.):
"() => { const zone=document.querySelector('<applied-zone-sel>'); return zone&&zone.innerText.includes('<label>')?'PASS:active':'FAIL:not active'; }"
```

---

## Other common patterns

```js
// Text present anywhere on the visible page:
"() => { return document.body.innerText.includes('<text>')?'PASS:found':'FAIL:not found'; }"

// Text content of a specific element (label, heading, badge):
"() => { const el=document.querySelector('<sel>'); const t=el?.textContent?.trim(); return t?'PASS:'+t:'FAIL:not found'; }"

// Current URL:
"() => { return window.location.href.includes('<path>')?'PASS:correct':'FAIL:'+window.location.href; }"
```

---

## Visual highlight in screenshots

To mark what was actually verified in the screenshot, apply a CSS outline to the found element **inside the `--js` function** as a side effect. This works for all assertions — including dropdowns and menus — because a style-attribute change on an existing element does not trigger DOM mutation observers and will not close open overlays. The outline is automatically removed by the cleanup step.

```js
// Highlight found element green (PASS), red (FAIL) — picked up in screenshot
"() => { const el=document.querySelector('<selector>'); if(!el) return 'FAIL:not found'; el.style.outline='3px solid green'; return 'PASS:'+el.textContent.trim(); }"

// Highlight the element that contains the wrong value so it's visible in the FAIL screenshot
"() => { const el=document.querySelector('<selector>'); if(!el) return 'FAIL:not found'; const val=el.getAttribute('<attr>'); if(val.includes('<wrong>')) { el.style.outline='3px solid red'; return 'FAIL:'+val; } el.style.outline='3px solid green'; return 'PASS:'+val; }"
```

Use `--selector` (the external argument) only for static elements on regular pages where you want a pointer label alongside the outline. For ephemeral UI (dropdowns, menus), always use the JS-inline approach — `--selector` appends a DOM node which closes the overlay before the screenshot fires.

---

## Checking an element's attribute value (href, text, state)

Always **find the element first, then read its value**. Never search only for elements that already carry the target value — the element exists regardless of its current state, and a selector that requires the new value returns null when the old value is present, producing a misleading "not found" failure.

```js
// ✅ correct — find the element, read its attribute, then decide PASS or FAIL
"() => { const el=document.querySelector('<selector>'); if(!el) return 'FAIL:element not found'; const val=el.getAttribute('<attr>')||el.textContent; return val.includes('<expected>')?'PASS:'+val:'FAIL:'+val; }"

// ❌ wrong — only finds elements that already have the new value; element still exists when it has old value
"() => { const el=document.querySelector('<selector>[<attr>*=\"<expected>\"]'); return el?'PASS:'+el.getAttribute('<attr>'):'FAIL:not found'; }"
```

**Internal names vs URL strings**: a resource name (route, service, object) does not always appear in the URL. When a TC says "link navigates to the new route", check the href against what you **know is wrong** (the old pattern) rather than looking for an internal resource name as a URL substring. Use `--inspect` to read the actual current value first if uncertain what the URL looks like.

---

## Key rules

- **Counting**: always exhaust pagination (`expand`) before counting DOM elements.
- **Exclusion**: verify via mechanism active + count < baseline — not per-item attribute checks.
- **Filter logic**: verify empirically — if combined > individual, the UI uses OR not AND.
- **Screenshot naming**: `--screenshot verify-<description>` (kept); `--screenshot inspect-<description>` (discarded on collect).
- **Assert the invariant, not the implementation.** Before writing JS, ask: "Is this testing what the TC is fundamentally about, or just a side effect?" Two patterns:
  - *Accessibility / reachability*: assert absence of error — `!body.includes('500')`, `!body.includes('Application is not available')`. Do NOT check for specific UI components (editor pane, console window, IDE layout) — these vary by image and config and will fail for reasons unrelated to the feature.
  - *Content / format*: assert the specific observable fact — URL pattern, field value, element presence — only when the content itself IS what is being verified.
