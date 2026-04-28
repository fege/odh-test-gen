#!/usr/bin/env python3
"""
ui_interact.py — Element interaction helper for test-plan.ui-verify.

Connects to the persistent Playwright browser started by ui_prepare.py.
Resolves elements via element-map.yaml, Playwright role locators, or JS evaluate.
Auto-relogins on OAuth session expiry — no manual intervention needed.

Usage:
    python3 ui_interact.py click  "<description>" [--section <section>]
    python3 ui_interact.py fill   "<description>" "<value>" [--section <section>] [--press-enter]
    python3 ui_interact.py goto   "<url>"
    python3 ui_interact.py scroll top|bottom
    python3 ui_interact.py expand
    python3 ui_interact.py wait   [ms]

Exit codes:
    0  success (or expand — always 0)
    1  element not found (click/fill) | unknown argument (scroll)
    2  wrong page / 404 / auth failed after relogin (goto only)
"""
import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("NODE_NO_WARNINGS", "1")

try:
    import yaml
    from playwright.sync_api import TimeoutError as PWTimeout
except ImportError as e:
    print(f"ERROR: {e} — run: pip install playwright pyyaml && playwright install chromium")
    sys.exit(1)

from paths import SKILL_DIR, TMP_DIR

from browser_common import get_page, release, do_oauth_login  # shared CDP connection logic

ELEMENT_MAP = SKILL_DIR / "element-map.yaml"
_MAP_CACHE: dict = {}


def load_map() -> dict:
    global _MAP_CACHE
    if not _MAP_CACHE and ELEMENT_MAP.exists():
        _MAP_CACHE = yaml.safe_load(ELEMENT_MAP.read_text()) or {}
    return _MAP_CACHE


def find_selector(description: str, section: str | None = None) -> str | None:
    element_map = load_map()
    desc_lower  = description.lower()
    sections    = ([section] if section else []) + [k for k in element_map if k != section] + ["general"]
    for s in sections:
        m = element_map.get(s, {})
        if desc_lower in m:
            return m[desc_lower]
        for key, sel in m.items():
            if desc_lower in key or key in desc_lower:
                return sel
    return None


# ── Auth recovery ─────────────────────────────────────────────────────────────

def _is_auth_page(page) -> bool:
    """Return True if the browser is on any auth/login page.

    Checks both URL patterns (standard OpenShift OAuth) and page content
    (oauth-proxy gate used by RHODS 2.x, served at the dashboard URL itself
    so the URL alone is not enough to detect it).
    """
    url = page.url
    if any(p in url for p in [
        "/oauth/authorize", "/login?", "/login/",
        "openshift-authentication", "/oauth2/callback",
    ]) or url.rstrip("/").endswith("/login"):
        return True
    # oauth-proxy (RHODS 2.x): shows "Log in with OpenShift" at the app URL
    try:
        return page.locator(
            'button:has-text("Log in with OpenShift"), '
            'a:has-text("Log in with OpenShift")'
        ).count() > 0
    except Exception:
        return False


def _relogin(page, ctx: dict) -> bool:
    """Complete the OAuth login flow from the current auth page.

    Reads credentials from test-variables.yml (password) and ui_context.json
    (username, idp). Returns True on success, False if login fails.
    """
    username = ctx.get("username", "")
    idp      = ctx.get("idp", "")

    tv_path = SKILL_DIR / "test-variables.yml"
    tv = yaml.safe_load(tv_path.read_text()) if tv_path.exists() else {}
    admin    = tv.get("admin_user", {}) or {}
    password = admin.get("password", "")

    print(f"  AUTH_REDIRECT detected — re-authenticating as {username}", flush=True)
    ok = do_oauth_login(page, username, password, idp, timeout=20000)
    if ok:
        print(f"  relogin: ✅ authenticated ({page.url[:60]})", flush=True)
    else:
        print(f"  relogin: still on auth page: {page.url}", flush=True)
    return ok


# ── Actions ───────────────────────────────────────────────────────────────────

def do_click(description: str, section: str | None) -> int:
    pw, browser, page, ctx = get_page()
    try:
        # 1. Element map
        sel = find_selector(description, section)
        if sel:
            try:
                el = page.query_selector(sel)
                if el:
                    el.scroll_into_view_if_needed()
                    el.click()
                    print(f"✅ click [{sel}]")
                    return 0
            except Exception:
                pass

        # 2. Exact text matching via locator
        for role in ["button", "link", "checkbox", "menuitem", "option"]:
            try:
                loc = page.get_by_role(role, name=description, exact=True)
                if loc.count() > 0:
                    loc.first.scroll_into_view_if_needed()
                    loc.first.click()
                    print(f"✅ click [role={role} text={description}]")
                    return 0
            except Exception:
                pass

        # 2.5. Partial accessible-name match via Playwright locator — handles button text variants
        # like "Load more" matching "Load more models". Restricted to action roles only (not form
        # controls) so checkboxes/options still require exact matches from Tier 2.
        for role in ["button", "link", "menuitem"]:
            try:
                loc = page.get_by_role(role, name=description)  # exact=False → substring match
                if loc.count() > 0:
                    loc.first.scroll_into_view_if_needed()
                    loc.first.click()
                    print(f"✅ click [role={role} contains={description!r}]")
                    return 0
            except Exception:
                pass

        # 3. Label text via evaluate — exact first, then prefix fallback.
        # Wrapped in try/except so any JS or Playwright error degrades to "not found" (exit 1)
        # rather than crashing the script with a traceback.
        try:
            match = page.evaluate(
                """(desc) => {
                    const els = [...document.querySelectorAll(
                        'button,a,label,input,span,[role=button],[role=checkbox],[role=menuitem]'
                    )];
                    const t = e => (e.textContent || '').trim();
                    const el = els.find(e => t(e) === desc || e.getAttribute('aria-label') === desc)
                              || els.find(e => t(e).startsWith(desc + ' ') || t(e).startsWith(desc + '\n'));
                    if (!el) return null;
                    el.scrollIntoView({block:'center'}); el.click();
                    const tag = el.tagName.toLowerCase();
                    const role = el.getAttribute('role') || '';
                    const label = (t(el) || el.getAttribute('aria-label') || '').slice(0, 60);
                    return role ? `${tag}[role=${role}] "${label}"` : `${tag} "${label}"`;
                }""",
                description,
            )
        except Exception:
            match = None
        if match:
            print(f"✅ click [js→ {match}]")
            return 0

        print(f"~ click: '{description}' — not found")
        return 1
    finally:
        release(pw)


def do_fill(description: str, value: str, section: str | None, press_enter: bool) -> int:
    pw, browser, page, ctx = get_page()
    try:
        # 1. Element map
        sel = find_selector(description, section)
        if sel:
            try:
                el = page.query_selector(sel)
                if el:
                    el.scroll_into_view_if_needed()
                    el.click()
                    el.fill(value)
                    if press_enter:
                        el.press("Enter")
                    print(f"✅ fill [{sel}] = '{value}'")
                    return 0
            except Exception:
                pass

        # 2. Find by placeholder / aria-label / name (actual inputs only)
        # Playwright's parameterised evaluate handles all escaping safely.
        try:
            found = page.evaluate(
                """(desc) => {
                    const inputs = [...document.querySelectorAll('input,textarea')];
                    const el = inputs.find(e => (
                        (e.placeholder||'').toLowerCase().includes(desc) ||
                        (e.getAttribute('aria-label')||'').toLowerCase().includes(desc) ||
                        (e.name||'').toLowerCase().includes(desc)
                    ));
                    if (el) { el.scrollIntoView({block:'center'}); el.focus(); return true; }
                    return false;
                }""",
                description.lower(),
            )
        except Exception:
            found = False
        if found:
            try:
                # Select-all + type to replace any existing content.
                # ControlOrMeta maps to Cmd on macOS and Ctrl on Linux/Windows.
                page.keyboard.press("ControlOrMeta+a")
                page.keyboard.type(value)
                if press_enter:
                    page.keyboard.press("Enter")
                print(f"✅ fill [eval input] = '{value}'")
                return 0
            except Exception:
                pass

        print(f"~ fill: '{description}' — not found")
        return 1
    finally:
        release(pw)


def _wait_for_spa(page) -> None:
    """Wait for a React SPA to finish rendering after navigation.

    Uses 'load' event (all JS evaluated, React has rendered) plus a brief
    function poll that ensures meaningful text is present. This is necessary
    because 'domcontentloaded' resolves before React Router runs.
    """
    try:
        page.wait_for_load_state("load", timeout=12000)
    except PWTimeout:
        pass
    try:
        page.wait_for_function(
            "() => document.body && document.body.innerText.trim().length > 50",
            timeout=8000,
        )
    except PWTimeout:
        pass


def do_goto(url: str) -> int:
    pw, browser, page, ctx = get_page()
    try:
        # Full page load via Playwright goto (equivalent to typing the URL in the address bar).
        # This causes a hard browser navigation — React unmounts entirely and remounts from scratch,
        # clearing all in-memory filter state, active tabs, and search terms.
        # The two-step reset in instructions (goto BASE_URL → goto TC_ENTRY_ROUTE) relies on this:
        # the first goto destroys the previous page's state, the second mounts the target fresh.
        # No reload() needed — goto already produces a full page load, and reload() can land on a
        # modified URL (pushed by the SPA) which would unexpectedly restore state.
        page.goto(url, wait_until="load", timeout=15000)
        _wait_for_spa(page)

        # Auto-recover from OAuth session expiry — no manual intervention needed
        if _is_auth_page(page):
            ok = _relogin(page, ctx)
            if not ok:
                print(f"WRONG_PAGE: re-authentication failed at {page.url}", flush=True)
                return 2
            page.goto(url, wait_until="load", timeout=15000)
            _wait_for_spa(page)

        # Detect 404 / error pages
        body  = page.inner_text("body") if page.query_selector("body") else ""
        title = page.title()
        is_404 = (
            "404" in title
            or "can't find that page" in body.lower()
            or "page not found" in body.lower()[:300]
            or len(body.strip()) < 30
        )
        if is_404:
            print(f"WRONG_PAGE: 404 or empty at {url}", flush=True)
            return 2

        print(f"Exit: 0", flush=True)
        return 0
    finally:
        release(pw)


def do_wait(ms: int) -> int:
    pw, browser, page, ctx = get_page()
    try:
        page.wait_for_timeout(ms)
        print(f"✅ wait [{ms}ms]")
        return 0
    finally:
        release(pw)


_SCROLL_CONTAINERS_JS = """
(dir) => {
    // Scroll the window in the requested direction
    if (dir === 'bottom') {
        window.scrollTo(0, document.body.scrollHeight);
    } else {
        window.scrollTo(0, 0);
    }
    // Also scroll any visible overflow-y containers (SPAs use these for main content —
    // window.scrollTo alone does not trigger lazy-load inside them).
    const val = dir === 'bottom' ? 999999 : 0;
    [...document.querySelectorAll('*')].forEach(el => {
        if (!el.clientHeight || el.clientHeight < 80) return;
        const oy = window.getComputedStyle(el).overflowY;
        if ((oy === 'auto' || oy === 'scroll') && el.scrollHeight > el.clientHeight + 10) {
            el.scrollTo(0, val);
        }
    });
}
"""


def do_scroll(target: str) -> int:
    """Scroll the page to trigger lazy loading or pagination.

    target: 'bottom' scrolls to end of page (triggers lazy load / reveals more items)
            'top'    scrolls back to the top

    Scrolls both the window and any overflow-y containers so that pagination
    buttons inside fixed-layout SPAs (e.g. ODH Dashboard) become visible.
    """
    pw, browser, page, ctx = get_page()
    try:
        if target in ("bottom", "top"):
            try:
                page.evaluate(_SCROLL_CONTAINERS_JS, target)
            except Exception:
                pass
        else:
            print(f"❌ scroll: unknown target '{target}' (use 'top' or 'bottom')")
            return 1
        # Brief pause so lazy-load handlers can fire
        try:
            page.wait_for_timeout(600)
        except Exception:
            pass
        print(f"✅ scroll [{target}]")
        return 0
    finally:
        release(pw)


_LOAD_MORE_JS = """
() => {
    // Click the first visible PAGINATION button outside tab navigation.
    // Pagination = loads more items into the main content list.
    // Deliberately excludes "+N more" and bare "Show more" — those are inline overflow
    // toggles for filter panels or card labels. Clicking them inflates the click count
    // without loading more main content, causing undercount of actual results.
    const isPagination = t =>
        /\\b(load|view)\\s+more\\b/i.test(t)         // "Load more", "View more", "Load more models"
        || /\\b(load|show|view)\\s+all\\b/i.test(t); // "Load all", "Show all", "View all"

    const btn = [...document.querySelectorAll('button,[role=button]')].find(el => {
        if (el.closest('[role="tablist"]')) return false;
        const r = el.getBoundingClientRect();
        return isPagination((el.textContent || '').trim()) && (r.width > 0 || r.height > 0);
    });
    if (btn) { btn.scrollIntoView({block: 'nearest'}); btn.click(); return true; }
    return false;
}
"""

_EXPAND_WITHIN_JS = """
(sel) => {
    // Click all visible disclosure buttons inside each matched container.
    // Scoped to the container — never touches tab navigation or page-level controls.
    // Works for any overflow pattern (+N more, Show more, View more, Expand, etc.)
    // regardless of the exact count or wording.
    const isDisclosure = t =>
        /^\\+?\\d+\\s+(more|less)/i.test(t)
        || /^(show|view|see|read)\\s+(more|less|all)/i.test(t)
        || /^expand(\\s.*)?$/i.test(t);

    const containers = [...document.querySelectorAll(sel)];
    let clicked = 0;
    containers.forEach(c => {
        [...c.querySelectorAll('button,[role=button]')].forEach(btn => {
            const r = btn.getBoundingClientRect();
            if (r.width === 0 && r.height === 0) return;
            if (!isDisclosure((btn.textContent || '').trim())) return;
            try { btn.scrollIntoView({block: 'nearest'}); btn.click(); clicked++; } catch (_) {}
        });
    });
    return clicked;
}
"""


def do_expand(selector: str) -> int:
    """Expand content — two modes depending on whether a selector is provided.

    No selector (default):
        Exhausts 'Load more' pagination — scrolls and clicks until no more pages.
        Safe to call on any page; never touches tab navigation.

    With selector (e.g. "[data-testid='model-catalog-card']"):
        Clicks every visible disclosure button (+N more, Show more, View more, Expand…)
        inside each element matched by the selector. Scoped to the container so it
        cannot accidentally trigger tab switches or page-level controls. Works for any
        overflow text — no need to know the exact count or wording.

    Exits 0 always.
    """
    pw, browser, page, ctx = get_page()
    try:
        if selector and selector != "all":
            # Scoped expansion inside specific containers
            try:
                n = page.evaluate(_EXPAND_WITHIN_JS, selector)
            except Exception:
                n = 0
            print(f"✅ expand: {n} toggle(s) in {selector!r}")
        else:
            # Default: exhaust Load more pagination only
            n_pages = 0
            while True:
                try:
                    page.evaluate(_SCROLL_CONTAINERS_JS, "bottom")
                    page.wait_for_timeout(400)
                    found = page.evaluate(_LOAD_MORE_JS)
                except Exception:
                    found = False
                if not found:
                    break
                n_pages += 1
            summary = f"{n_pages} 'Load more' page(s)" if n_pages else "nothing to load"
            print(f"✅ expand: {summary}")
        return 0
    finally:
        release(pw)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["click", "fill", "goto", "wait", "scroll", "expand"])
    parser.add_argument("args", nargs="*")
    parser.add_argument("--section",     default=None)
    parser.add_argument("--press-enter", action="store_true")
    opts = parser.parse_args()

    required = {"click": 1, "fill": 2, "goto": 1, "wait": 0, "scroll": 1, "expand": 0}
    if len(opts.args) < required[opts.action]:
        parser.error(
            f"'{opts.action}' requires {required[opts.action]} argument(s), "
            f"got {len(opts.args)}"
        )

    if opts.action == "click":
        sys.exit(do_click(opts.args[0], opts.section))
    elif opts.action == "fill":
        sys.exit(do_fill(opts.args[0], opts.args[1], opts.section, opts.press_enter))
    elif opts.action == "goto":
        sys.exit(do_goto(opts.args[0]))
    elif opts.action == "wait":
        ms = int(opts.args[0]) if opts.args else 1000
        sys.exit(do_wait(ms))
    elif opts.action == "scroll":
        sys.exit(do_scroll(opts.args[0]))
    elif opts.action == "expand":
        target = opts.args[0] if opts.args else "all"
        sys.exit(do_expand(target))


if __name__ == "__main__":
    main()
