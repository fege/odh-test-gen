#!/usr/bin/env python3
"""
ui_assert.py — Generic assertion runner for test-plan.ui-verify.

Connects to the persistent Playwright browser started by ui_prepare.py.
Runs a JavaScript check, shows a visual banner with the result, takes a
highlighted screenshot, and logs to the TC log.

Usage:
    python3 ui_assert.py \\
        --tc <TC_ID> \\
        --what "<description of what is being checked>" \\
        --expected "<what should be true>" \\
        --js "() => { ...; return 'PASS:detail' or 'FAIL:reason'; }" \\
        --screenshot <filename-suffix> \\
        [--selector <css-selector>]
        [--inspect]   # diagnostic only — never logs to TC log, always exits 0

The JS must return a string starting with PASS: or FAIL: followed by detail.
page.evaluate() returns Python objects directly — no stdout parsing needed.

Exit codes: 0 = PASS (or --inspect), 1 = FAIL, 2 = WRONG PAGE (retry with different URL — nothing logged)

--inspect usage:
    When an ER assertion fails and you need to understand the DOM before writing a better
    assertion, use --inspect for one diagnostic call. It prints the JS result and takes a
    screenshot but does NOT affect the TC log or verdict.
"""
import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("NODE_NO_WARNINGS", "1")

try:
    from playwright.sync_api import TimeoutError as PWTimeout
except ImportError:
    print("ERROR: playwright not installed — run: pip install playwright && playwright install chromium")
    sys.exit(1)

from paths import SKILL_DIR, TMP_DIR

from browser_common import get_page, release  # shared CDP connection logic

TC_LOG    = TMP_DIR / "ui_tc_log.json"
SESSION   = TMP_DIR / ".ui-session"


def update_log(tc_id: str, what: str, expected: str, result: str, detail: str,
               replace: bool = False, title: str = "", screenshot: str = "") -> None:
    log = {}
    if TC_LOG.exists():
        try:
            log = json.loads(TC_LOG.read_text())
        except Exception:
            pass
    if tc_id not in log:
        log[tc_id] = {"title": tc_id, "verdict": "PASS", "assertions": [], "blocked_reason": ""}

    # Update title if a real one is provided (not just the ID placeholder)
    if title and log[tc_id].get("title") == tc_id:
        log[tc_id]["title"] = title

    if replace:
        # Remove any previous assertion with the same 'checked' text so a re-assertion
        # after fixing page state doesn't leave ghost FAIL entries in the log.
        log[tc_id]["assertions"] = [
            a for a in log[tc_id]["assertions"] if a["checked"] != what
        ]

    # Warn if the same assertion is logged again without --replace so Claude knows to use it
    if not replace and any(a.get("checked") == what for a in log[tc_id]["assertions"]):
        print(f"  ⚠️  '{what}' logged twice for {tc_id} without --replace — "
              f"use --replace to avoid duplicate entries", flush=True)

    entry = {"checked": what, "expected": expected, "result": result, "detail": detail}
    if screenshot:
        entry["screenshot"] = screenshot
    log[tc_id]["assertions"].append(entry)

    # Recalculate verdict from all remaining assertions (needed after --replace removes stale entries).
    # Priority: FAIL > INCOMPLETE > BLOCKED > PASS.
    # INCOMPLETE is set at TC level by ui_block.py --incomplete and has no assertion entry;
    # preserve it so a passing re-assert cannot silently clear an interrupted TC.
    current_verdict = log[tc_id].get("verdict", "PASS")
    all_results = [a["result"] for a in log[tc_id]["assertions"]]
    if "FAIL" in all_results:
        log[tc_id]["verdict"] = "FAIL"
    elif current_verdict == "INCOMPLETE":
        log[tc_id]["verdict"] = "INCOMPLETE"
    elif "BLOCKED" in all_results:
        log[tc_id]["verdict"] = "BLOCKED"
    else:
        log[tc_id]["verdict"] = "PASS"

    TC_LOG.parent.mkdir(parents=True, exist_ok=True)
    TC_LOG.write_text(json.dumps(log, indent=2))


def _wait_animations(page) -> None:
    """Wait for all non-infinite CSS animations/transitions to finish.

    Adapts to actual animation duration — not a fixed delay. Infinite animations
    (spinners, pulses) are excluded. Uses Playwright's page-default timeout as
    safety net; falls through silently on timeout.
    """
    try:
        page.wait_for_function(
            "() => !document.getAnimations().filter("
            "  a => a.playState === 'running'"
            "    && a.effect && a.effect.getTiming().iterations !== Infinity"
            ").length"
        )
    except Exception:
        pass


def _click_element(page, description: str) -> str | None:
    """Try to click an element matching description. Returns a label string on success, None otherwise.

    Tier 1: Playwright role-based (exact then partial).
    Tier 2: JS text / aria-label scan.
    """
    for exact in (True, False):
        for role in ("button", "link", "menuitem", "tab"):
            try:
                loc = page.get_by_role(role, name=description, exact=exact)
                if loc.count() > 0:
                    loc.first.scroll_into_view_if_needed()
                    loc.first.click()
                    label = "exact" if exact else "partial"
                    return f"role={role} {label}={description!r}"
            except Exception:
                continue

    try:
        match = page.evaluate(
            """(desc) => {
                const els = [...document.querySelectorAll(
                    'button,a,[role=button],[role=menuitem],[role=tab]'
                )];
                const t = e => (e.textContent || '').trim();
                const el = els.find(e => t(e) === desc || e.getAttribute('aria-label') === desc)
                          || els.find(e => t(e).startsWith(desc + ' ') || t(e).startsWith(desc + '\\n'));
                if (!el) return null;
                el.scrollIntoView({block: 'center'}); el.click();
                return (t(el) || el.getAttribute('aria-label') || '').slice(0, 60);
            }""",
            description,
        )
        if match:
            return f"js→ {match!r}"
    except Exception:
        pass

    return None


def _click_before(page, description: str) -> bool:
    """Click an element to open ephemeral UI state (dropdown, menu, accordion) before asserting.

    Returns True to continue with the assertion, False if the click caused unintended
    navigation (caller should return exit 2 / WRONG_PAGE in that case).
    If the element is not found the function still returns True — the JS assertion
    that follows will FAIL with the real reason, which is the correct logged outcome.
    """
    from urllib.parse import urlparse
    url_before = page.url

    label = _click_element(page, description)
    if label:
        _wait_animations(page)
        print(f"  --click-before: ✅ [{label}]", flush=True)
    else:
        print(
            f"  --click-before: ⚠️  '{description}' not found — "
            f"proceeding; assertion will report the actual failure",
            flush=True,
        )
        return True  # let the JS assertion run and FAIL with the real reason

    # Navigation guard: if the click sent us to an auth page or a different origin, abort.
    # A hash or query-string change on the same origin is fine (tab switches, anchors).
    url_after = page.url
    if url_before != url_after:
        b, a = urlparse(url_before), urlparse(url_after)
        if b.netloc != a.netloc or any(p in a.path for p in ("/oauth/", "/login")):
            print(
                f"  --click-before: ⚠️  unintended navigation "
                f"{url_before!r} → {url_after!r}",
                flush=True,
            )
            return False  # caller will return exit 2 (WRONG_PAGE)

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tc",           required=True)
    parser.add_argument("--title",        default="",  help="Human-readable TC title (stored in log for report)")
    parser.add_argument("--what",         required=True)
    parser.add_argument("--expected",     default="")
    parser.add_argument("--js",           required=True)
    parser.add_argument("--screenshot",   default="verify")
    parser.add_argument("--selector",     default="")
    parser.add_argument("--click-before",          default="",
                        help="Click this element before asserting. Use for ephemeral UI state "
                             "(dropdowns, menus, accordions) that close between separate tool calls.")
    parser.add_argument("--expected-url-contains", default="",
                        help="Abort with WRONG_PAGE (exit 2) if the current URL does not contain "
                             "this string. Use to guard against asserting on the wrong page or tab.")
    parser.add_argument("--retry",                 type=int, default=0,
                        help="Retry the JS assertion up to N times (500 ms apart) on FAIL before "
                             "logging. Use for async-updating UI or animations that may not have "
                             "settled. Default: 0 (no retry).")
    parser.add_argument("--inspect",      action="store_true",
                        help="Diagnostic only — run JS and screenshot but DO NOT log to TC log or change verdict")
    parser.add_argument("--replace",      action="store_true",
                        help="Replace any previous assertion with the same --what text for this TC. "
                             "Use when re-asserting after fixing page state to remove ghost FAIL entries.")
    args = parser.parse_args()

    pw, browser, page, _ctx = get_page()
    try:
        # 1. Wait for page stability — readyState, no active loading indicators, meaningful content.
        #    Falls through on timeout so a slow page never hard-blocks the assertion.
        #    Loading detection is generic:
        #      - aria-busy="true"  ARIA standard, framework-agnostic
        #      - [class*="pf-"][class*="-c-spinner"]  matches pf-c-spinner, pf-v5-c-spinner,
        #        pf-v6-c-spinner, any future pf-vN-c-spinner — no version pinning needed.
        #        On non-PF pages querySelector returns null (falsy) → branch not taken → no-op.
        try:
            page.wait_for_function(
                "() => {"
                "  if (document.readyState !== 'complete' || !document.body) return false;"
                "  var sel = '[aria-busy=\"true\"]"
                ",[class*=\"pf-\"][class*=\"-c-spinner\"]"
                ",[class*=\"pf-\"][class*=\"-c-skeleton\"]';"
                "  if (document.querySelector(sel)) return false;"
                "  return document.body.innerText.trim().length > 50;"
                "}",
                timeout=8000,
            )
        except PWTimeout:
            pass

        # 2. Detect 404 / wrong page — return exit code 2 so caller can retry
        body = page.inner_text("body") if page.query_selector("body") else ""
        is_404 = (
            "404" in page.title()
            or "can't find that page" in body.lower()
            or len(body.strip()) < 30
        )
        if is_404:
            print(f"WRONG_PAGE: 404 or empty at {page.url}", flush=True)
            return 2

        # 3. Inject the banner BEFORE click-before so the dropdown opens into an already-
        #    stable DOM. If the banner were appended after the dropdown opens, its
        #    document.body.appendChild call would fire a DOM mutation that triggers the
        #    dropdown's close handler. Injecting first means only style-attribute changes
        #    happen while the dropdown is open — those don't trigger childList observers.
        safe_what = args.what.replace("'", " ").replace('"', " ")[:120]
        try:
            page.evaluate(
                "([text]) => {"
                " let b = document.getElementById('ui-banner');"
                " if (!b) { b = document.createElement('div'); b.id = 'ui-banner';"
                " b.style = 'position:fixed;top:0;left:0;right:0;padding:10px 16px;"
                "z-index:2147483647;font:bold 14px monospace;white-space:nowrap;overflow:hidden;';"
                " document.body.appendChild(b); }"
                " b.style.background = 'rgba(0,50,150,0.88)'; b.style.color = '#fff';"
                " b.textContent = text; }",
                [f"Checking: {safe_what}"]
            )
        except Exception:
            pass

        # 4. Click-before — open ephemeral UI state (dropdown/menu) before asserting.
        #    Banner is already in the DOM, so no further appendChild mutations will fire.
        if args.click_before:
            if not _click_before(page, args.click_before):
                print(f"WRONG_PAGE: --click-before caused navigation to {page.url}", flush=True)
                return 2

        # 4b. URL pre-check — abort if the current page is not what the assertion expects.
        if args.expected_url_contains and args.expected_url_contains not in page.url:
            print(
                f"WRONG_PAGE: expected URL containing {args.expected_url_contains!r}, "
                f"got {page.url!r}",
                flush=True,
            )
            return 2

        # 4. Hide banner, run assertion (with optional retry), restore banner.
        #    Banner stays hidden for the full retry window — prevents its text from
        #    appearing in innerText checks inside the JS assertion.
        try:
            page.evaluate("() => { const b=document.getElementById('ui-banner'); if(b) b.style.visibility='hidden'; }")
        except Exception:
            pass

        raw = f"FAIL:assertion did not run"
        for _attempt in range(max(1, args.retry + 1)):
            # On retry with --click-before: re-click so a toggled-closed container
            # gets toggled open again before the JS re-runs.
            if _attempt > 0 and args.click_before:
                lbl = _click_element(page, args.click_before)
                if lbl:
                    _wait_animations(page)
            try:
                raw = page.evaluate(args.js)  # direct Python return — no stdout parsing!
            except Exception as e:
                raw = f"FAIL:JS error — {str(e)[:120]}"
            if not isinstance(raw, str):
                raw = str(raw)
            if raw.startswith("PASS") or _attempt >= args.retry:
                break
            print(f"  retry {_attempt + 1}/{args.retry} (assertion not yet PASS)…", flush=True)
            page.wait_for_timeout(500)

        try:
            page.evaluate("() => { const b=document.getElementById('ui-banner'); if(b) b.style.visibility='visible'; }")
        except Exception:
            pass

        if not isinstance(raw, str):
            raw = str(raw)
        passed = raw.startswith("PASS")
        result = "PASS" if passed else "FAIL"
        detail = raw.split(":", 1)[1].strip() if ":" in raw else raw

        # 5. Update banner to green/red result
        icon    = "PASS" if passed else "FAIL"
        color   = "rgba(0,120,0,0.90)" if passed else "rgba(160,0,0,0.90)"
        outline = "green" if passed else "red"
        bg      = "rgba(0,200,0,0.06)" if passed else "rgba(200,0,0,0.06)"
        banner_text = f"{icon}: {safe_what} — {detail[:80]}"
        try:
            page.evaluate(
                "([text, color]) => { const b=document.getElementById('ui-banner'); if(b){b.style.background=color;b.textContent=text;} }",
                [banner_text, color]
            )
        except Exception:
            pass

        # 6. Screenshot — taken BEFORE selector highlight so any open overlay (dropdown,
        #    menu, popover) is still in the DOM. The highlight step below appends elements
        #    to document.body which can trigger mutation-based close handlers on overlays.
        SESSION.mkdir(parents=True, exist_ok=True)
        safe_suffix = args.screenshot[:40].replace(" ", "-").lower()
        fname = SESSION / f"{args.tc}-{safe_suffix}.png"
        try:
            page.screenshot(path=str(fname))
        except Exception:
            pass  # screenshot failure never blocks the assertion result

        # 7. Optional: highlight the target element with pointer label (after screenshot
        #    so DOM mutations don't close open overlays before the image is captured)
        if args.selector:
            safe_sel = args.selector.replace("'", "\\'")
            safe_label = args.what.replace("'", " ").replace('"', " ")[:60]
            try:
                page.evaluate(
                    f"([sel, outline, bg, color, label]) => {{"
                    f" document.getElementById('ui-pointer')?.remove();"
                    f" const el = document.querySelector(sel);"
                    f" if (el) {{"
                    f"  el.scrollIntoView({{block:'center'}});"
                    f"  el.style.outline='3px solid '+outline;"
                    f"  el.style.background=bg;"
                    f"  const rect=el.getBoundingClientRect();"
                    f"  const p=document.createElement('div'); p.id='ui-pointer';"
                    f"  p.style='position:fixed;z-index:2147483646;background:'+color+';color:#fff;"
                    f"font:bold 11px monospace;padding:3px 8px;border-radius:3px;"
                    f"top:'+Math.max(50,rect.top-30)+'px;left:'+Math.max(0,Math.min(rect.left,window.innerWidth-320))+'px;"
                    f"max-width:320px;white-space:nowrap;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.4);';"
                    f"  p.textContent='▶ '+label; document.body.appendChild(p);"
                    f" }}"
                    f"}}",
                    [args.selector, outline, bg, color, args.what[:60]]
                )
                # Second screenshot with element highlighted
                page.screenshot(path=str(fname))
            except Exception:
                pass

        # 8. Clean up overlays
        try:
            page.evaluate(
                "() => {"
                " document.getElementById('ui-banner')?.remove();"
                " document.getElementById('ui-pointer')?.remove();"
                " document.querySelectorAll('[style*=\"3px solid\"]').forEach(e=>{e.style.outline='';e.style.background='';});"
                "}"
            )
        except Exception:
            pass

        # 9. Log result — skipped for --inspect calls (diagnostic only)
        if args.inspect:
            prefix = "🔍"
            print(f"{prefix} [INSPECT] {args.what}: {detail}")
            return 0  # inspect never fails — it's diagnostic
        else:
            update_log(args.tc, args.what, args.expected, result, detail,
                       replace=args.replace,
                       title=args.title,
                       screenshot=fname.name if fname.exists() else "")
            status = "✅" if passed else "❌"
            print(f"{status} {args.what}: {detail}")
            return 0 if passed else 1

    finally:
        release(pw)


if __name__ == "__main__":
    sys.exit(main())
