#!/usr/bin/env python3
"""
ui_report.py — Generate report.html and report.md from tc_log.json.

Reads tc_log.json and ui_context.json from the session directory and produces
a human-readable HTML report with screenshot thumbnails and a plain-text
Markdown summary.

Usage:
    python3 ui_report.py <session_dir>   # explicit path (recommended)
    python3 ui_report.py                 # finds most recent session in results/
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from paths import SKILL_DIR, TMP_DIR

# ── Verdict metadata ──────────────────────────────────────────────────────────

_VERDICT_RANK  = {"FAIL": 0, "INCOMPLETE": 1, "BLOCKED": 2, "PASS": 3}
_VERDICT_EMOJI = {"PASS": "✅", "FAIL": "❌", "BLOCKED": "⚠️", "INCOMPLETE": "🔴"}

# (foreground, light-background) per verdict
_VERDICT_COLOR = {
    "PASS":       ("#1a7f37", "#dafbe1"),
    "FAIL":       ("#cf222e", "#ffebe9"),
    "BLOCKED":    ("#bc4c00", "#fff1e5"),
    "INCOMPLETE": ("#6639ba", "#fbefff"),
}

_PRIORITY_COLOR = {
    "P0": ("#82071e", "#ffcdd2"),
    "P1": ("#7d4e00", "#fff3cd"),
    "P2": ("#0550ae", "#dbeafe"),
}


import re as _re


def _strip_tc_prefix(title: str, tc_id: str) -> str:
    """Remove 'TC-XXX: ' or 'TC-XXX — ' prefix from a title when TC ID is already shown separately."""
    for sep in (f"{tc_id}: ", f"{tc_id} \u2014 ", f"{tc_id} - ", f"{tc_id}:"):
        if title.startswith(sep):
            return title[len(sep):].strip()
    return title


def _format_source_html(source: str) -> str:
    """Format the source field as HTML. 'PR #3 (https://…)' → clickable link."""
    m = _re.match(r'^(PR #\d+)\s*\(?(https?://[^)]+?)\)?$', source.strip())
    if m:
        return f'<a href="{_esc(m.group(2))}" target="_blank">{_esc(m.group(1))}</a>'
    if source.startswith("http"):
        return f'<a href="{_esc(source)}" target="_blank">{_esc(source)}</a>'
    return _esc(source)


def _overall_verdict(tc_log: dict) -> str:
    if not tc_log:
        return "PASS"
    return min(
        (e.get("verdict", "PASS") for e in tc_log.values()),
        key=lambda v: _VERDICT_RANK.get(v, 99),
    )


def _esc(s: str) -> str:
    """Minimal HTML-escape for user-supplied strings."""
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _badge(verdict: str, small: bool = False) -> str:
    fg, bg = _VERDICT_COLOR.get(verdict, ("#555", "#eee"))
    em = _VERDICT_EMOJI.get(verdict, verdict)
    size = "0.72em" if small else "0.82em"
    return (
        f'<span style="display:inline-block;padding:2px 9px;border-radius:20px;'
        f'font-size:{size};font-weight:700;background:{bg};color:{fg};'
        f'border:1px solid {fg}33;white-space:nowrap;">{em}&nbsp;{verdict}</span>'
    )


def _priority_badge(priority: str) -> str:
    fg, bg = _PRIORITY_COLOR.get(priority, ("#555", "#f0f0f0"))
    return (
        f'<span style="display:inline-block;padding:1px 7px;border-radius:20px;'
        f'font-size:0.72em;font-weight:600;background:{bg};color:{fg};">{priority}</span>'
    )


# ── HTML generation ───────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px; line-height: 1.6; color: #1f2328;
    background: #f6f8fa; padding: 24px 16px;
}
.page { max-width: 1040px; margin: 0 auto; }

/* ── header ── */
.header {
    background: #fff; border: 1px solid #d0d7de; border-radius: 10px;
    padding: 22px 26px; margin-bottom: 16px;
}
.header h1 { font-size: 1.35em; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.header .meta { color: #656d76; font-size: 0.85em; margin-top: 8px; }
.header .meta a { color: #0969da; text-decoration: none; }
.header .meta a:hover { text-decoration: underline; }

/* ── stat boxes ── */
.stats { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
.stat {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 12px 20px; border-radius: 8px; min-width: 96px;
    border: 1px solid transparent; cursor: pointer; user-select: none;
    transition: outline 0.1s;
}
.stat .n { font-size: 2em; font-weight: 700; line-height: 1.1; }
.stat .l { font-size: 0.72em; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px; }
.s-pass       { background: #dafbe1; color: #1a7f37; border-color: #1a7f3733; }
.s-fail       { background: #ffebe9; color: #cf222e; border-color: #cf222e33; }
.s-blocked    { background: #fff1e5; color: #bc4c00; border-color: #bc4c0033; }
.s-incomplete { background: #fbefff; color: #6639ba; border-color: #6639ba33; }
.stat.active  { outline: 2px solid #0969da; outline-offset: 3px; }

/* ── card wrapper ── */
.card {
    background: #fff; border: 1px solid #d0d7de; border-radius: 10px;
    margin-bottom: 14px; overflow: hidden;
}
.card-title {
    padding: 11px 16px; font-size: 0.82em; font-weight: 600; color: #656d76;
    background: #f6f8fa; border-bottom: 1px solid #d0d7de;
    text-transform: uppercase; letter-spacing: 0.06em;
}

/* ── overview table ── */
table.ov { width: 100%; border-collapse: collapse; }
table.ov th {
    text-align: left; padding: 8px 14px; font-size: 0.79em; font-weight: 600;
    color: #656d76; background: #f6f8fa; border-bottom: 1px solid #d0d7de;
    text-transform: uppercase; letter-spacing: 0.05em;
}
table.ov td { padding: 9px 14px; border-bottom: 1px solid #eaecef; vertical-align: middle; }
table.ov tr:last-child td { border-bottom: none; }
table.ov tr:hover td { background: #f6f8fa; }
.mono { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.88em; font-weight: 600; }

/* ── TC detail sections ── */
details.tc {
    background: #fff; border: 1px solid #d0d7de; border-radius: 10px;
    margin-bottom: 12px; overflow: hidden;
}
details.tc > summary {
    padding: 13px 16px; cursor: pointer; user-select: none;
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    list-style: none; border-bottom: 1px solid transparent;
}
details.tc[open] > summary { border-bottom-color: #d0d7de; background: #f6f8fa; }
details.tc > summary::-webkit-details-marker { display: none; }
.chevron { font-size: 0.65em; color: #656d76; flex-shrink: 0; transition: transform 0.15s; }
details.tc[open] .chevron { transform: rotate(90deg); }
.tc-name { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.9em; font-weight: 700; }
.tc-desc { font-weight: 500; flex: 1; }

.tc-body { padding: 18px; }
.objective {
    color: #656d76; font-size: 0.88em; margin-bottom: 14px;
    padding: 9px 14px; background: #f6f8fa; border-radius: 6px;
    border-left: 3px solid #d0d7de;
}

/* ── assertion table ── */
table.asr { width: 100%; border-collapse: collapse; font-size: 0.88em; }
table.asr th {
    text-align: left; padding: 7px 12px; font-size: 0.79em; font-weight: 600;
    color: #656d76; background: #f6f8fa; border-bottom: 1px solid #d0d7de;
    text-transform: uppercase; letter-spacing: 0.05em;
}
table.asr td { padding: 9px 12px; border-bottom: 1px solid #eaecef; vertical-align: top; }
table.asr tr:last-child td { border-bottom: none; }
/* shrink Result and Screenshot to content width; Checked and Detail fill the rest */
table.asr .col-tight { width: 1px; white-space: nowrap; }
.row-pass       td { background: #f6fff8; }
.row-fail       td { background: #fff8f8; }
.row-blocked    td { background: #fffbf0; }
.row-incomplete td { background: #fdf4ff; }

/* ── screenshots ── */
.shot-wrap { display: inline-block; }
.shot {
    display: block; height: 110px; max-width: 200px;
    border: 1px solid #d0d7de; border-radius: 5px;
    cursor: zoom-in;
    object-fit: cover; object-position: top;
    transition: opacity 0.15s, box-shadow 0.15s;
}
.shot:hover { opacity: 0.82; box-shadow: 0 2px 8px rgba(0,0,0,0.18); }

/* ── lightbox ── */
#lb {
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.88); z-index: 9999;
    align-items: center; justify-content: center; cursor: zoom-out;
}
#lb.open { display: flex; }
#lb-img {
    max-width: 92vw; max-height: 90vh; border-radius: 8px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.6); object-fit: contain; cursor: default;
}
#lb-close {
    position: absolute; top: 16px; right: 20px; color: #fff;
    font-size: 20px; cursor: pointer; opacity: 0.75;
    background: rgba(255,255,255,0.12); border-radius: 50%;
    width: 34px; height: 34px; display: flex; align-items: center; justify-content: center;
}
#lb-close:hover { opacity: 1; background: rgba(255,255,255,0.22); }
#lb-caption {
    position: absolute; bottom: 18px; left: 50%; transform: translateX(-50%);
    color: rgba(255,255,255,0.75); font-size: 0.8em;
    background: rgba(0,0,0,0.5); padding: 4px 14px; border-radius: 20px;
    max-width: 80vw; text-align: center; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; pointer-events: none;
}

/* ── blocked reason ── */
.blocked-note {
    margin-top: 14px; padding: 9px 14px; border-radius: 6px;
    background: #fff1e5; border: 1px solid #bc4c0033; color: #7d3700;
    font-size: 0.88em;
}

/* ── failure analysis ── */
.failure-card { border-color: #cf222e55; }
.failure-card .card-title { background: #ffebe9; color: #cf222e; border-bottom-color: #cf222e22; }
table.fa { width: 100%; border-collapse: collapse; }
table.fa th {
    text-align: left; padding: 8px 14px; font-size: 0.79em; font-weight: 600;
    color: #656d76; background: #f6f8fa; border-bottom: 1px solid #d0d7de;
    text-transform: uppercase;
}
table.fa td { padding: 9px 14px; border-bottom: 1px solid #eaecef; vertical-align: top; }
table.fa tr:last-child td { border-bottom: none; }

footer { text-align: center; color: #8c959f; font-size: 0.78em; margin-top: 20px; }

/* ── filter bar ── */
.filter-bar {
    display: flex; gap: 20px; align-items: center; flex-wrap: wrap;
    background: #fff; border: 1px solid #d0d7de; border-radius: 10px;
    padding: 12px 16px; margin-bottom: 14px;
    position: sticky; top: 8px; z-index: 50;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.filter-group { display: flex; align-items: center; gap: 6px; }
.filter-sep { width: 1px; background: #d0d7de; align-self: stretch; }
.filter-label {
    font-size: 0.75em; font-weight: 600; color: #8c959f;
    text-transform: uppercase; letter-spacing: 0.06em; margin-right: 2px;
}
.fbtn {
    padding: 3px 11px; border-radius: 20px; border: 1px solid #d0d7de;
    background: #fff; cursor: pointer; font-size: 0.82em; color: #57606a;
    font-family: inherit; transition: border-color 0.1s, background 0.1s, color 0.1s;
}
.fbtn:hover { border-color: #0969da; color: #0969da; }
.fbtn.active { background: #0969da; border-color: #0969da; color: #fff; font-weight: 600; }
.no-results {
    text-align: center; padding: 32px; color: #8c959f;
    font-style: italic; display: none;
}
"""


def _format_date(prepared: str) -> str:
    try:
        return datetime.strptime(prepared, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d %H:%M")
    except Exception:
        return prepared or datetime.now().strftime("%Y-%m-%d %H:%M")


def generate_html(tc_log: dict, ctx: dict, session_dir: Path) -> str:
    feature  = _esc(ctx.get("feature", "unknown"))
    source   = ctx.get("source", "")
    target   = ctx.get("target_url", "")
    cluster  = _esc(ctx.get("cluster_api", ""))
    user     = _esc(ctx.get("username", ""))
    strat    = _esc(ctx.get("strat_key", ""))
    date_str = _format_date(ctx.get("prepared_at", ""))

    tc_meta = {tc["id"]: tc for tc in ctx.get("test_cases", [])}

    # ── stats ─────────────────────────────────────────────────────────────────
    counts = {v: 0 for v in ("PASS", "FAIL", "BLOCKED", "INCOMPLETE")}
    for e in tc_log.values():
        counts[e.get("verdict", "PASS")] = counts.get(e.get("verdict", "PASS"), 0) + 1

    overall = _overall_verdict(tc_log)

    stat_cls = {"PASS": "s-pass", "FAIL": "s-fail", "BLOCKED": "s-blocked", "INCOMPLETE": "s-incomplete"}
    stats_html = "".join(
        f'<div class="stat {stat_cls[v]}" data-value="{v}" title="Filter to {v}">'
        f'<span class="n">{counts[v]}</span>'
        f'<span class="l">{_VERDICT_EMOJI[v]} {v}</span>'
        f'</div>'
        for v in ("PASS", "FAIL", "BLOCKED", "INCOMPLETE")
    )

    # ── meta line ─────────────────────────────────────────────────────────────
    meta_parts = [f'<strong>{date_str}</strong>']
    if source:
        meta_parts.append(_format_source_html(source))
    if user:
        meta_parts.append(f'{user}')
    if cluster:
        meta_parts.append(f'Cluster: <code>{cluster}</code>')
    if strat:
        meta_parts.append(f'Strategy: {strat}')
    if target:
        meta_parts.append(f'Target: <a href="{_esc(target)}" target="_blank">{_esc(target)}</a>')
    meta_html = ' &nbsp;·&nbsp; '.join(meta_parts)

    # ── overview table ────────────────────────────────────────────────────────
    ov_rows = []
    for tc_id, entry in tc_log.items():
        verdict  = entry.get("verdict", "PASS")
        meta     = tc_meta.get(tc_id, {})
        title    = entry.get("title", tc_id)
        if title == tc_id:
            title = meta.get("title", tc_id)
        title = _strip_tc_prefix(title, tc_id)
        priority = meta.get("priority", "")
        n_pass   = sum(1 for a in entry.get("assertions", []) if a.get("result") == "PASS")
        n_fail   = sum(1 for a in entry.get("assertions", []) if a.get("result") == "FAIL")
        n_blk    = sum(1 for a in entry.get("assertions", []) if a.get("result") == "BLOCKED")
        parts = []
        if n_pass: parts.append(f'{n_pass} ✅')
        if n_fail: parts.append(f'{n_fail} ❌')
        if n_blk:  parts.append(f'{n_blk} ⚠️')
        checks = ' &nbsp; '.join(parts) if parts else '—'
        ov_rows.append(
            f'<tr data-verdict="{verdict}" data-priority="{priority}" data-tc="{_esc(tc_id)}" style="cursor:pointer;" title="Jump to {_esc(tc_id)}">'
            f'<td><span class="mono">{_esc(tc_id)}</span></td>'
            f'<td>{_esc(title)}</td>'
            f'<td>{_priority_badge(priority) if priority else ""}</td>'
            f'<td style="white-space:nowrap;">{checks}</td>'
            f'<td>{_badge(verdict)}</td>'
            f'</tr>'
        )

    overview_html = (
        '<div class="card">'
        '<div class="card-title">Overview</div>'
        '<table class="ov"><thead><tr>'
        '<th>TC</th><th>Title</th><th>Priority</th><th>Checks</th><th>Verdict</th>'
        '</tr></thead>'
        f'<tbody>{"".join(ov_rows)}</tbody>'
        '</table></div>'
    )

    # ── TC detail sections ────────────────────────────────────────────────────
    tc_sections = []
    for tc_id, entry in tc_log.items():
        verdict  = entry.get("verdict", "PASS")
        meta     = tc_meta.get(tc_id, {})
        title    = entry.get("title", tc_id)
        if title == tc_id:
            title = meta.get("title", tc_id)
        title = _strip_tc_prefix(title, tc_id)
        priority    = meta.get("priority", "")
        objective   = meta.get("objective", "")
        blocked_rsn = _esc(entry.get("blocked_reason", ""))
        assertions  = entry.get("assertions", [])

        # FAIL and INCOMPLETE expand by default; PASS/BLOCKED collapse
        open_attr = " open" if verdict in ("FAIL", "INCOMPLETE") else ""

        # Assertion rows
        arows = []
        for a in assertions:
            r        = a.get("result", "")
            row_cls  = f"row-{r.lower()}"
            shot     = a.get("screenshot", "")
            if shot and (session_dir / shot).exists():
                shot_html = (
                    f'<div class="shot-wrap">'
                    f'<img class="shot" src="./{_esc(shot)}"'
                    f' alt="{_esc(a.get("checked","")[:80])}"'
                    f' data-src="./{_esc(shot)}">'
                    f'</div>'
                )
            else:
                shot_html = '<span style="color:#8c959f;font-size:0.8em;">—</span>'

            expected_full = a.get("expected", "")
            checked_title = (f' title="{_esc(expected_full)}"' if expected_full else "")

            cursor = ' style="cursor:help;"' if expected_full else ""
            arows.append(
                f'<tr class="{row_cls}">'
                f'<td{checked_title}{cursor}>{_esc(a.get("checked",""))}</td>'
                f'<td class="col-tight">{_badge(r, small=True)}</td>'
                f'<td>{_esc(a.get("detail",""))}</td>'
                f'<td class="col-tight">{shot_html}</td>'
                f'</tr>'
            )

        objective_html = (
            f'<div class="objective">📋 {_esc(objective)}</div>'
            if objective else ""
        )
        blocked_html = (
            f'<div class="blocked-note">⚠️ <strong>Blocked:</strong> {blocked_rsn}</div>'
            if blocked_rsn else ""
        )
        asr_table = (
            '<table class="asr"><thead><tr>'
            '<th>Checked <span style="font-weight:400;opacity:0.6;">(hover for expected)</span></th>'
            '<th class="col-tight">Result</th>'
            '<th>Detail</th>'
            '<th class="col-tight">Screenshot</th>'
            f'</tr></thead><tbody>{"".join(arows)}</tbody></table>'
            if arows
            else '<p style="color:#8c959f;font-style:italic;padding:4px 0;">No assertions recorded.</p>'
        )

        p_badge = _priority_badge(priority) if priority else ""
        tc_sections.append(
            f'<details class="tc"{open_attr} data-verdict="{verdict}" data-priority="{priority}" id="tc-{_esc(tc_id)}">'
            f'<summary>'
            f'<span class="chevron">▶</span>'
            f'{_badge(verdict)}'
            f'&nbsp;<span class="tc-name">{_esc(tc_id)}</span>'
            f'&nbsp;{p_badge}'
            f'&nbsp;<span class="tc-desc">— {_esc(title)}</span>'
            f'</summary>'
            f'<div class="tc-body">'
            f'{objective_html}'
            f'{asr_table}'
            f'{blocked_html}'
            f'</div>'
            f'</details>'
        )

    # ── failure analysis ──────────────────────────────────────────────────────
    failures = [
        (tc_id, e) for tc_id, e in tc_log.items()
        if e.get("verdict") in ("FAIL", "INCOMPLETE")
    ]
    failure_html = ""
    if failures:
        fa_rows = []
        for tc_id, entry in failures:
            meta  = tc_meta.get(tc_id, {})
            title = entry.get("title", tc_id)
            if title == tc_id:
                title = meta.get("title", tc_id)
            failed_details = [
                _esc(a["detail"])
                for a in entry.get("assertions", [])
                if a.get("result") == "FAIL"
            ]
            cause = "<br>".join(failed_details) or _esc(entry.get("blocked_reason", "—"))
            fa_rows.append(
                f'<tr>'
                f'<td><span class="mono">{_esc(tc_id)}</span><br>'
                f'<span style="color:#656d76;font-size:0.85em;">{_esc(_strip_tc_prefix(title, tc_id))}</span></td>'
                f'<td>{_badge(entry["verdict"], small=True)}</td>'
                f'<td>{cause}</td>'
                f'</tr>'
            )
        failure_html = (
            '<div class="card failure-card">'
            '<div class="card-title">❌ Failure Analysis</div>'
            '<table class="fa"><thead><tr>'
            '<th>TC</th><th>Verdict</th><th>Root Cause</th>'
            f'</tr></thead><tbody>{"".join(fa_rows)}</tbody></table>'
            '</div>'
        )

    # ── filter bar ───────────────────────────────────────────────────────────
    present_verdicts   = [v for v in ("PASS", "FAIL", "BLOCKED", "INCOMPLETE") if counts[v] > 0]
    present_priorities = sorted({tc_meta.get(tid, {}).get("priority", "") for tid in tc_log} - {""})

    verdict_btns = "".join(
        f'<button class="fbtn" data-filter="verdict" data-value="{v}">'
        f'{_VERDICT_EMOJI[v]} {v}</button>'
        for v in present_verdicts
    )
    priority_btns = "".join(
        f'<button class="fbtn" data-filter="priority" data-value="{p}">{p}</button>'
        for p in present_priorities
    )
    filter_bar = (
        '<div class="filter-bar">'
        '<span class="filter-label">Verdict</span>'
        f'<div class="filter-group">{verdict_btns}</div>'
        + ('<div class="filter-sep"></div>'
           '<span class="filter-label">Priority</span>'
           f'<div class="filter-group">{priority_btns}</div>'
           if priority_btns else "")
        + '<span id="filter-count" style="margin-left:auto;font-size:0.8em;color:#8c959f;white-space:nowrap;display:none;"></span>'
        + '</div>'
        + '<p class="no-results" id="no-results">No test cases match the current filter.</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ui-verify — {feature}</title>
  <style>{_CSS}</style>
</head>
<body>
<div class="page">

  <div class="header">
    <h1>test-plan.ui-verify &mdash; {feature} &nbsp; {_badge(overall)}</h1>
    <div class="meta">{meta_html}</div>
    <div class="stats">{stats_html}</div>
  </div>

  {overview_html}

  {filter_bar}

  {"".join(tc_sections)}

  {failure_html}

  <footer>Generated by test-plan.ui-verify &nbsp;·&nbsp; {date_str}</footer>

</div>

<!-- lightbox -->
<div id="lb">
  <img id="lb-img" src="" alt="">
  <div id="lb-close">✕</div>
  <div id="lb-caption"></div>
</div>
<script>
  const lb    = document.getElementById('lb');
  const lbImg = document.getElementById('lb-img');
  const lbCap = document.getElementById('lb-caption');
  function openLb(src, caption) {{
    lbImg.src = src;
    lbCap.textContent = caption;
    lb.classList.add('open');
    document.body.style.overflow = 'hidden';
  }}
  function closeLb() {{
    lb.classList.remove('open');
    document.body.style.overflow = '';
    lbImg.src = '';
  }}
  lb.addEventListener('click', closeLb);
  document.getElementById('lb-close').addEventListener('click', function(e) {{ e.stopPropagation(); closeLb(); }});
  lbImg.addEventListener('click', function(e) {{ e.stopPropagation(); }});
  document.addEventListener('keydown', function(e) {{ if (e.key === 'Escape') closeLb(); }});
  document.querySelectorAll('.shot').forEach(function(img) {{
    img.addEventListener('click', function(e) {{
      e.preventDefault();
      openLb(img.getAttribute('data-src') || img.src, img.alt);
    }});
  }});

  // ── filters ──
  var activeVerdict  = null;
  var activePriority = null;
  var noResults   = document.getElementById('no-results');
  var filterCount = document.getElementById('filter-count');
  var totalTCs    = document.querySelectorAll('details.tc').length;

  function syncUI() {{
    document.querySelectorAll('.fbtn[data-filter="verdict"]').forEach(function(b) {{
      b.classList.toggle('active', b.dataset.value === activeVerdict);
    }});
    document.querySelectorAll('.fbtn[data-filter="priority"]').forEach(function(b) {{
      b.classList.toggle('active', b.dataset.value === activePriority);
    }});
    document.querySelectorAll('.stat[data-value]').forEach(function(el) {{
      el.classList.toggle('active', el.dataset.value === activeVerdict);
    }});
  }}

  function applyFilters() {{
    var tcs    = document.querySelectorAll('details.tc');
    var ovRows = document.querySelectorAll('table.ov tbody tr');
    var visible = 0;
    tcs.forEach(function(el) {{
      var show = (!activeVerdict  || el.dataset.verdict  === activeVerdict)
              && (!activePriority || el.dataset.priority === activePriority);
      el.style.display = show ? '' : 'none';
      if (show) visible++;
    }});
    ovRows.forEach(function(el) {{
      var show = (!activeVerdict  || el.dataset.verdict  === activeVerdict)
              && (!activePriority || el.dataset.priority === activePriority);
      el.style.display = show ? '' : 'none';
    }});
    noResults.style.display = (visible === 0) ? 'block' : 'none';
    if (activeVerdict || activePriority) {{
      filterCount.textContent = visible + ' of ' + totalTCs + ' shown';
      filterCount.style.display = '';
    }} else {{
      filterCount.style.display = 'none';
    }}
  }}

  function setFilter(type, val) {{
    if (type === 'verdict')  activeVerdict  = (activeVerdict  === val) ? null : val;
    else                     activePriority = (activePriority === val) ? null : val;
    syncUI();
    applyFilters();
  }}

  // filter bar buttons
  document.querySelectorAll('.fbtn').forEach(function(btn) {{
    btn.addEventListener('click', function() {{ setFilter(btn.dataset.filter, btn.dataset.value); }});
  }});

  // stat boxes → verdict shortcut
  document.querySelectorAll('.stat[data-value]').forEach(function(el) {{
    el.addEventListener('click', function() {{ setFilter('verdict', el.dataset.value); }});
  }});

  // overview row → jump to TC section
  document.querySelectorAll('table.ov tbody tr[data-tc]').forEach(function(row) {{
    row.addEventListener('click', function() {{
      var tc = document.getElementById('tc-' + row.dataset.tc);
      if (!tc) return;
      tc.setAttribute('open', '');
      tc.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      tc.style.outline = '2px solid #0969da';
      tc.style.outlineOffset = '2px';
      setTimeout(function() {{ tc.style.outline = ''; tc.style.outlineOffset = ''; }}, 1200);
    }});
  }});
</script>
</body>
</html>"""


# ── Markdown generation ───────────────────────────────────────────────────────

def generate_md(tc_log: dict, ctx: dict) -> str:
    feature  = ctx.get("feature", "unknown")
    source   = ctx.get("source", "")
    target   = ctx.get("target_url", "")
    cluster  = ctx.get("cluster_api", "")
    user     = ctx.get("username", "")
    strat    = ctx.get("strat_key", "")
    date_str = _format_date(ctx.get("prepared_at", ""))

    tc_meta = {tc["id"]: tc for tc in ctx.get("test_cases", [])}

    counts  = {v: 0 for v in ("PASS", "FAIL", "BLOCKED", "INCOMPLETE")}
    for e in tc_log.values():
        counts[e.get("verdict", "PASS")] = counts.get(e.get("verdict", "PASS"), 0) + 1
    overall = _overall_verdict(tc_log)

    lines = []
    lines += [
        f"# test-plan.ui-verify — {feature}",
        "",
        f"**Overall: {_VERDICT_EMOJI.get(overall, '')} {overall}**",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Date** | {date_str} |",
    ]
    if source:
        lines.append(f"| **Source** | {source} |")
    if strat:
        lines.append(f"| **Strategy** | {strat} |")
    if target:
        lines.append(f"| **Target** | {target} |")
    if user:
        lines.append(f"| **User** | {user} |")
    if cluster:
        lines.append(f"| **Cluster** | {cluster} |")

    lines += [
        "",
        "## Summary",
        "",
        "| Verdict | Count |",
        "|---------|------:|",
    ]
    for v in ("PASS", "FAIL", "BLOCKED", "INCOMPLETE"):
        lines.append(f"| {_VERDICT_EMOJI[v]} {v} | {counts[v]} |")

    lines += ["", "## Results", ""]

    for tc_id, entry in tc_log.items():
        verdict    = entry.get("verdict", "PASS")
        meta       = tc_meta.get(tc_id, {})
        title      = entry.get("title", tc_id)
        if title == tc_id:
            title = meta.get("title", tc_id)
        title = _strip_tc_prefix(title, tc_id)
        priority    = meta.get("priority", "")
        objective   = meta.get("objective", "")
        blocked_rsn = entry.get("blocked_reason", "")
        assertions  = entry.get("assertions", [])

        em   = _VERDICT_EMOJI.get(verdict, verdict)
        p_str = f" `{priority}`" if priority else ""
        lines.append(f"### {em} {verdict} &nbsp; `{tc_id}`{p_str} — {title}")
        lines.append("")

        if objective:
            lines += [f"> {objective}", ""]

        if assertions:
            lines += [
                "| Checked | Expected | Result | Detail |",
                "|---------|----------|--------|--------|",
            ]
            for a in assertions:
                r   = a.get("result", "")
                em_r = _VERDICT_EMOJI.get(r, r)
                lines.append(
                    f"| {a.get('checked','')} | {a.get('expected','')} "
                    f"| {em_r} {r} | {a.get('detail','')} |"
                )
            lines.append("")

            # screenshots — relative paths render in VS Code preview and GitHub
            shots = [a["screenshot"] for a in assertions if a.get("screenshot")]
            seen  = set()
            for shot in shots:
                if shot not in seen:
                    seen.add(shot)
                    lines.append(f"![{shot}](./{shot})")
            if seen:
                lines.append("")

        if blocked_rsn:
            lines += [f"**Blocked:** {blocked_rsn}", ""]

        lines.append("---")
        lines.append("")

    # Failure analysis
    failures = [
        (tc_id, e) for tc_id, e in tc_log.items()
        if e.get("verdict") in ("FAIL", "INCOMPLETE")
    ]
    if failures:
        lines += ["## Failure Analysis", "", "| TC | Verdict | Root Cause |", "|----|---------|------------|"]
        for tc_id, entry in failures:
            verdict = entry.get("verdict", "")
            causes  = [a["detail"] for a in entry.get("assertions", []) if a.get("result") == "FAIL"]
            cause   = "; ".join(causes) or entry.get("blocked_reason", "")
            lines.append(f"| `{tc_id}` | {_VERDICT_EMOJI.get(verdict,'')} {verdict} | {cause} |")
        lines.append("")

    return "\n".join(lines)


# ── Upgrade comparison report ─────────────────────────────────────────────────

_OUTCOME_COLOR = {
    "FIXED":        ("#1a7f37", "#dafbe1"),   # green
    "REGRESSION":   ("#cf222e", "#ffebe9"),   # red
    "STABLE-PASS":  ("#656d76", "#f6f8fa"),   # grey
    "STABLE-BLOCK": ("#bc4c00", "#fff1e5"),   # orange
    "CHANGED":      ("#6639ba", "#fbefff"),   # purple
    "POST-ONLY":    ("#0550ae", "#dbeafe"),   # blue — ran in post but had no pre baseline
}
_OUTCOME_LABEL = {
    "FIXED":        "✅ FIXED",
    "REGRESSION":   "❌ REGRESSION",
    "STABLE-PASS":  "➡ STABLE",
    "STABLE-BLOCK": "⚠️ STILL FAILING",
    "CHANGED":      "↕ CHANGED",
    "POST-ONLY":    "🆕 POST-ONLY",
}


def _upgrade_outcome(pre_v: str, post_v: str) -> str:
    """Classify the change between pre and post verdicts.

    pre_v / post_v are verdict strings or '—' when the TC was not present
    in that run (e.g. a post-only TC with upgrade_phase: post has no pre entry).
    """
    if pre_v == "—":
        return "POST-ONLY"   # TC not in baseline — no comparison possible
    if pre_v in ("FAIL", "BLOCKED", "INCOMPLETE") and post_v == "PASS":
        return "FIXED"
    if pre_v == "PASS" and post_v in ("FAIL", "INCOMPLETE"):
        return "REGRESSION"
    if pre_v == post_v == "PASS":
        return "STABLE-PASS"
    if pre_v in ("FAIL", "BLOCKED", "INCOMPLETE") and post_v in ("FAIL", "BLOCKED", "INCOMPLETE"):
        return "STABLE-BLOCK"
    return "CHANGED"


def _collect_preconditions(pre_ctx: dict, post_ctx: dict) -> list[str]:
    """Collect unique manual preconditions from all TCs across both runs."""
    seen, result = set(), []
    for ctx in (pre_ctx, post_ctx):
        for tc in ctx.get("test_cases", []):
            for pre in tc.get("preconditions", []):
                if pre not in seen:
                    seen.add(pre)
                    result.append(pre)
    return result


def _upgrade_cleanup_html(pre_ctx: dict, post_ctx: dict) -> str:
    """HTML cleanup reminder section for the upgrade report."""
    preconditions = _collect_preconditions(pre_ctx, post_ctx)
    if not preconditions:
        return ""
    items = "".join(f'<li style="margin:4px 0;">{_esc(p)}</li>' for p in preconditions)
    return (
        '<div style="background:#fff;border:1px solid #d0d7de;border-radius:10px;'
        'margin-top:16px;overflow:hidden;">'
        '<div style="padding:11px 16px;font-size:0.82em;font-weight:600;color:#656d76;'
        'background:#fffbf0;border-bottom:1px solid #d0d7de;text-transform:uppercase;'
        'letter-spacing:0.06em;">🧹 Cleanup reminder</div>'
        '<div style="padding:14px 18px;font-size:0.88em;">'
        '<p style="margin:0 0 10px;color:#57606a;">Upgrade verification is complete. '
        'The following resources were provisioned manually for this test and '
        '<strong>were not cleaned up automatically</strong>. '
        'Delete them when you no longer need the upgrade test environment:</p>'
        f'<ul style="margin:0;padding-left:20px;color:#1f2328;">{items}</ul>'
        '</div></div>'
    )


def _upgrade_cleanup_md(pre_ctx: dict, post_ctx: dict) -> list[str]:
    """Markdown cleanup reminder lines for the upgrade report."""
    preconditions = _collect_preconditions(pre_ctx, post_ctx)
    if not preconditions:
        return []
    lines = [
        "## 🧹 Cleanup Reminder",
        "",
        "Upgrade verification is complete. The following resources were provisioned "
        "manually and **were not cleaned up automatically**. "
        "Delete them when you no longer need the upgrade test environment:",
        "",
    ]
    for p in preconditions:
        lines.append(f"- {p}")
    lines.append("")
    return lines


def generate_upgrade_html(pre_log: dict, post_log: dict,
                          pre_ctx: dict, post_ctx: dict,
                          session_dir: Path) -> str:
    """Generate a side-by-side upgrade comparison report."""
    feature    = post_ctx.get("feature", pre_ctx.get("feature", "unknown"))
    pre_date   = _format_date(pre_ctx.get("prepared_at", ""))
    post_date  = _format_date(post_ctx.get("prepared_at", ""))
    pre_target = pre_ctx.get("target_url", "")
    post_target= post_ctx.get("target_url", "")
    source     = post_ctx.get("source", "")

    # Build tc_meta from both contexts
    tc_meta = {tc["id"]: tc for tc in pre_ctx.get("test_cases", [])}
    tc_meta.update({tc["id"]: tc for tc in post_ctx.get("test_cases", [])})

    # All TC IDs across both runs
    all_ids = list(dict.fromkeys(list(pre_log.keys()) + list(post_log.keys())))

    counts = {k: 0 for k in ("FIXED", "REGRESSION", "STABLE-PASS", "STABLE-BLOCK", "CHANGED", "POST-ONLY")}
    rows = []
    for tc_id in all_ids:
        pre_e  = pre_log.get(tc_id, {})
        post_e = post_log.get(tc_id, {})
        pre_v  = pre_e.get("verdict", "—")
        post_v = post_e.get("verdict", "—")
        outcome = _upgrade_outcome(pre_v, post_v)
        counts[outcome] = counts.get(outcome, 0) + 1

        meta    = tc_meta.get(tc_id, {})
        title   = _strip_tc_prefix(post_e.get("title", pre_e.get("title", tc_id)), tc_id)
        if title == tc_id:
            title = _strip_tc_prefix(meta.get("title", tc_id), tc_id)
        priority = meta.get("priority", "")
        up_phase = meta.get("upgrade_phase", "")

        fg, bg = _OUTCOME_COLOR.get(outcome, ("#333", "#eee"))
        label  = _OUTCOME_LABEL.get(outcome, outcome)
        badge  = (f'<span style="display:inline-block;padding:2px 9px;border-radius:20px;'
                  f'font-size:0.8em;font-weight:700;background:{bg};color:{fg};">{label}</span>')

        open_attr = ' open' if outcome == "REGRESSION" else ""
        phase_tag = (f'&nbsp;<span style="font-size:0.72em;background:#e8f4ff;'
                     f'color:#0550ae;padding:1px 6px;border-radius:10px;">{up_phase}</span>'
                     if up_phase else "")

        rows.append(
            f'<details{open_attr} style="background:#fff;border:1px solid #d0d7de;'
            f'border-radius:8px;margin-bottom:8px;overflow:hidden;">'
            f'<summary style="padding:11px 14px;cursor:pointer;display:flex;align-items:center;gap:8px;">'
            f'{badge}'
            f'&nbsp;<span style="font-family:monospace;font-weight:700;">{_esc(tc_id)}</span>'
            f'{_priority_badge(priority) if priority else ""}'
            f'{phase_tag}'
            f'&nbsp;<span style="font-weight:500;">{_esc(title)}</span>'
            f'</summary>'
            f'<div style="padding:12px 16px;border-top:1px solid #d0d7de;">'
            f'<table style="width:100%;border-collapse:collapse;font-size:0.88em;">'
            f'<thead><tr style="background:#f6f8fa;">'
            f'<th style="padding:6px 10px;text-align:left;border-bottom:1px solid #d0d7de;">Phase</th>'
            f'<th style="padding:6px 10px;text-align:left;border-bottom:1px solid #d0d7de;">Verdict</th>'
            f'<th style="padding:6px 10px;text-align:left;border-bottom:1px solid #d0d7de;">Detail</th>'
            f'</tr></thead><tbody>'
            f'<tr><td style="padding:8px 10px;border-bottom:1px solid #eaecef;">Pre-upgrade</td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #eaecef;">{_badge(pre_v)}</td>'
            f'<td style="padding:8px 10px;border-bottom:1px solid #eaecef;">'
            f'{_esc(pre_e.get("blocked_reason","") or "")}' + "".join(
                f'{_esc(a.get("detail",""))}<br>' for a in pre_e.get("assertions",[])
                if a.get("result") in ("FAIL","BLOCKED")
            ) + f'</td></tr>'
            f'<tr><td style="padding:8px 10px;">Post-upgrade</td>'
            f'<td style="padding:8px 10px;">{_badge(post_v)}</td>'
            f'<td style="padding:8px 10px;">'
            f'{_esc(post_e.get("blocked_reason","") or "")}' + "".join(
                f'{_esc(a.get("detail",""))}<br>' for a in post_e.get("assertions",[])
                if a.get("result") in ("FAIL","BLOCKED")
            ) + f'</td></tr>'
            f'</tbody></table>'
            f'</div></details>'
        )

    # Summary bar
    def _stat(label, key, bg, fg):
        return (f'<div style="display:flex;flex-direction:column;align-items:center;'
                f'padding:10px 18px;border-radius:8px;background:{bg};color:{fg};min-width:90px;">'
                f'<span style="font-size:1.8em;font-weight:700;">{counts[key]}</span>'
                f'<span style="font-size:0.72em;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">'
                f'{label}</span></div>')

    stats = (
        _stat("✅ Fixed",       "FIXED",        "#dafbe1", "#1a7f37") +
        _stat("❌ Regression",  "REGRESSION",   "#ffebe9", "#cf222e") +
        _stat("➡ Stable",      "STABLE-PASS",  "#f6f8fa", "#656d76") +
        _stat("⚠ Still failing","STABLE-BLOCK","#fff1e5", "#bc4c00") +
        _stat("↕ Changed",     "CHANGED",      "#fbefff", "#6639ba") +
        _stat("🆕 Post-only",  "POST-ONLY",    "#dbeafe", "#0550ae")
    )

    source_html = _format_source_html(source) if source else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Upgrade Report — {_esc(feature)}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 14px; line-height: 1.6; color: #1f2328;
            background: #f6f8fa; padding: 24px 16px; }}
    .page {{ max-width: 960px; margin: 0 auto; }}
    .header {{ background: #fff; border: 1px solid #d0d7de; border-radius: 10px;
               padding: 20px 24px; margin-bottom: 14px; }}
    .header h1 {{ font-size: 1.3em; }}
    .meta {{ color: #656d76; font-size: 0.85em; margin-top: 6px; }}
    .meta a {{ color: #0969da; text-decoration: none; }}
    .stats {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
    details > summary {{ user-select: none; list-style: none; }}
    details > summary::-webkit-details-marker {{ display: none; }}
    footer {{ text-align: center; color: #8c959f; font-size: 0.78em; margin-top: 18px; }}
  </style>
</head>
<body><div class="page">
  <div class="header">
    <h1>⬆ Upgrade Verification — {_esc(feature)}</h1>
    <div class="meta">
      Pre-upgrade: <strong>{pre_date}</strong> · {_esc(pre_target)}<br>
      Post-upgrade: <strong>{post_date}</strong> · {_esc(post_target)}
      {"<br>Source: " + source_html if source_html else ""}
    </div>
    <div style="display:flex;gap:10px;margin-top:12px;flex-wrap:wrap;">
      <a href="./pre-session/report.html" target="_blank"
         style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;
                border-radius:6px;background:#f6f8fa;border:1px solid #d0d7de;
                color:#1f2328;text-decoration:none;font-size:0.85em;font-weight:500;">
        📋 Pre-upgrade report
      </a>
      <a href="./report.html" target="_blank"
         style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;
                border-radius:6px;background:#f6f8fa;border:1px solid #d0d7de;
                color:#1f2328;text-decoration:none;font-size:0.85em;font-weight:500;">
        📋 Post-upgrade report
      </a>
    </div>
    <div class="stats">{stats}</div>
  </div>
  {"".join(rows)}
  {_upgrade_cleanup_html(pre_ctx, post_ctx)}
  <footer>Generated by test-plan.ui-verify upgrade comparison</footer>
</div></body></html>"""


def generate_upgrade_md(pre_log: dict, post_log: dict,
                        pre_ctx: dict, post_ctx: dict) -> str:
    """Plain-text upgrade comparison summary."""
    feature   = post_ctx.get("feature", pre_ctx.get("feature", "unknown"))
    pre_date  = _format_date(pre_ctx.get("prepared_at", ""))
    post_date = _format_date(post_ctx.get("prepared_at", ""))
    tc_meta   = {tc["id"]: tc for tc in pre_ctx.get("test_cases", [])}
    tc_meta.update({tc["id"]: tc for tc in post_ctx.get("test_cases", [])})

    all_ids = list(dict.fromkeys(list(pre_log.keys()) + list(post_log.keys())))
    counts  = {k: 0 for k in ("FIXED", "REGRESSION", "STABLE-PASS", "STABLE-BLOCK", "CHANGED", "POST-ONLY")}
    tc_rows = []

    for tc_id in all_ids:
        pre_v  = pre_log.get(tc_id, {}).get("verdict", "—")
        post_v = post_log.get(tc_id, {}).get("verdict", "—")
        outcome = _upgrade_outcome(pre_v, post_v)
        counts[outcome] = counts.get(outcome, 0) + 1
        label = _OUTCOME_LABEL.get(outcome, outcome)
        title = _strip_tc_prefix(tc_meta.get(tc_id, {}).get("title", tc_id), tc_id)
        tc_rows.append(f"| `{tc_id}` | {label} | {_VERDICT_EMOJI.get(pre_v, pre_v)} {pre_v} | {_VERDICT_EMOJI.get(post_v, post_v)} {post_v} | {title} |")

    lines = [
        f"# Upgrade Verification — {feature}",
        "",
        f"[📋 Pre-upgrade report](./pre-session/report.md) &nbsp;·&nbsp; [📋 Post-upgrade report](./report.md)",
        "",
        f"| | |",
        f"|---|---|",
        f"| **Pre-upgrade** | {pre_date} |",
        f"| **Post-upgrade** | {post_date} |",
        "",
        "## Summary",
        "",
        "| Outcome | Count |",
        "|---------|------:|",
    ]
    for k, lbl in _OUTCOME_LABEL.items():
        lines.append(f"| {lbl} | {counts[k]} |")
    lines += [
        "",
        "## Results",
        "",
        "| TC | Outcome | Pre | Post | Title |",
        "|----|---------|-----|------|-------|",
    ] + tc_rows + [""] + _upgrade_cleanup_md(pre_ctx, post_ctx)

    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) > 1:
        session = Path(sys.argv[1]).resolve()
    else:
        # Fall back to most recent session in results/
        results_dir = SKILL_DIR / "results"
        sessions = sorted(results_dir.glob("uiv-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not sessions:
            print("ERROR: no session directory found. Pass the path as an argument.", file=sys.stderr)
            sys.exit(1)
        session = sessions[0].resolve()
        print(f"  Using most recent session: {session}")

    tc_log_path = session / "tc_log.json"
    ctx_path    = session / "ui_context.json"

    if not tc_log_path.exists():
        print(f"ERROR: tc_log.json not found in {session}", file=sys.stderr)
        sys.exit(1)

    tc_log = json.loads(tc_log_path.read_text(encoding="utf-8"))
    ctx    = json.loads(ctx_path.read_text(encoding="utf-8")) if ctx_path.exists() else {}

    html = generate_html(tc_log, ctx, session)
    md   = generate_md(tc_log, ctx)

    html_path = session / "report.html"
    md_path   = session / "report.md"

    html_path.write_text(html, encoding="utf-8")
    md_path.write_text(md,   encoding="utf-8")

    print(f"  HTML report : {html_path}")
    print(f"  MD report   : {md_path}")
    print(f"  Open in browser: open '{html_path}'")

    # ── Upgrade comparison report (post runs only) ────────────────────────────
    baseline_dir = ctx.get("upgrade_baseline_dir", "")
    if baseline_dir:
        pre_session   = Path(baseline_dir)
        pre_log_path  = pre_session / "tc_log.json"
        pre_ctx_path  = pre_session / "ui_context.json"
        if pre_log_path.exists():
            pre_log = json.loads(pre_log_path.read_text(encoding="utf-8"))
            pre_ctx = json.loads(pre_ctx_path.read_text(encoding="utf-8")) if pre_ctx_path.exists() else {}
            ug_html = generate_upgrade_html(pre_log, tc_log, pre_ctx, ctx, session)
            ug_md   = generate_upgrade_md(pre_log, tc_log, pre_ctx, ctx)
            ug_html_path = session / "upgrade-report.html"
            ug_md_path   = session / "upgrade-report.md"
            ug_html_path.write_text(ug_html, encoding="utf-8")
            ug_md_path.write_text(ug_md,   encoding="utf-8")

            # Symlink pre-session inside post session so both are navigable together
            symlink = session / "pre-session"
            try:
                if symlink.exists() or symlink.is_symlink():
                    symlink.unlink()
                symlink.symlink_to(pre_session.resolve())
                print(f"  ⬆  Pre-session  : {symlink} → {pre_session.resolve()}")
            except Exception as e:
                print(f"  ⚠️  Could not create pre-session symlink: {e}")

            print(f"\n  ⬆  Upgrade report: {ug_html_path}")
            print(f"  Open in browser: open '{ug_html_path}'")
        else:
            print(f"\n  ⚠️  Baseline tc_log.json not found at {pre_log_path} — skipping upgrade report")


if __name__ == "__main__":
    main()
