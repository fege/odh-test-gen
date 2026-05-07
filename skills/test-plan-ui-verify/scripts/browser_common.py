#!/usr/bin/env python3
"""
browser_common.py — Shared browser connection helpers for test-plan.ui-verify.

Provides get_page() and release() used by ui_interact.py and ui_assert.py.
Centralised here so CDP connection logic is maintained in one place.
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("NODE_NO_WARNINGS", "1")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed — run: pip install playwright && playwright install chromium")
    sys.exit(1)

from paths import SKILL_DIR, TMP_DIR

def get_page():
    """Connect to the persistent browser and return (playwright, browser, page, ctx).

    Uses contexts[-1] (the login context created by ui_prepare.py, not the
    default empty CDP context at index 0) and pages[-1] (the most recently
    active page). This is consistent across all script calls.
    """
    ctx_path = TMP_DIR / "ui_context.json"
    if not ctx_path.exists():
        print("ERROR: ui_context.json not found — run ui_prepare.py first", file=sys.stderr)
        sys.exit(1)
    ctx = json.loads(ctx_path.read_text())
    cdp = ctx.get("browser_cdp")
    if not cdp:
        print("ERROR: No browser CDP endpoint — run ui_prepare.py first", file=sys.stderr)
        sys.exit(1)

    try:
        pw      = sync_playwright().start()
        browser = pw.chromium.connect_over_cdp(cdp)
    except Exception as e:
        print(f"ERROR: Cannot connect to browser ({e}) — run ui_prepare.py first", file=sys.stderr)
        sys.exit(1)

    # Always use the last context (login context) and its FIRST page.
    # contexts[0] is the default empty CDP context; login creates contexts[1+].
    # pages[0] is the original app window created during login.
    # pages[-1] would be wrong if a popup or new tab opened — those are appended
    # after pages[0]. We close any extra pages to keep the context clean.
    contexts = browser.contexts
    if contexts:
        ctx_b = contexts[-1]
        if not ctx_b.pages:
            page = ctx_b.new_page()
        else:
            page = ctx_b.pages[0]
            # Close unexpected popups / new tabs that may have opened
            for extra in ctx_b.pages[1:]:
                try:
                    extra.close()
                except Exception:
                    pass
    else:
        ctx_b = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = ctx_b.new_page()

    return pw, browser, page, ctx


def release(pw) -> None:
    """Stop playwright library. CDP browser subprocess keeps running independently."""
    pw.stop()


def do_oauth_login(page, username: str, password: str, idp: str,
                   timeout: int = 20000) -> bool:
    """Perform the OpenShift OAuth login flow: click IDP → fill credentials → wait.

    Shared by ui_prepare.py (initial login) and ui_interact.py (_relogin).
    Returns True if login succeeded, False otherwise.
    Each caller handles its own error-recovery on False.
    """
    # Wait for the auth page to finish loading before inspecting the DOM.
    # Without this, count() / wait_for() can run before IDP buttons render.
    page.wait_for_load_state("networkidle")

    # RHODS 2.x uses oauth-proxy in front of the dashboard, which shows an
    # intermediate "Log in with OpenShift" page before the IDP selector.
    # 3.x goes directly to the IDP page — this step is silently skipped there.
    for selector in [
        'button:has-text("Log in with OpenShift")',
        'a:has-text("Log in with OpenShift")',
    ]:
        try:
            loc = page.locator(selector)
            loc.first.wait_for(state="visible", timeout=3000)
            loc.first.click()
            page.wait_for_load_state("networkidle")
            break
        except Exception:
            continue

    # Click IDP selector.  Use wait_for(visible) so we don't race against
    # rendering.  Short per-attempt timeout because we're trying alternatives —
    # a wrong selector should fail fast so the next one can be tried.
    idp_clicked = False
    for selector in [
        f'button:text-is("{idp}")',
        f'button:has-text("{idp}")',
        f'a:text-is("{idp}")',
        f'a:has-text("{idp}")',
    ]:
        try:
            loc = page.locator(selector)
            loc.first.wait_for(state="visible", timeout=3000)
            loc.first.click()
            page.wait_for_load_state("networkidle")
            idp_clicked = True
            break
        except Exception:
            continue

    if not idp_clicked:
        print(f"  IDP '{idp}' not found at {page.url} — assuming cluster skips IDP selection",
              flush=True)

    # Fill username — wait_for with no timeout uses Playwright's page default (30 s)
    try:
        user_loc = page.locator('[name="username"], #username, input[type="text"]')
        user_loc.first.wait_for(state="visible")
        user_loc.first.fill(username)
    except Exception as e:
        print(f"  ❌ Login: username field not found at {page.url} — {e}", flush=True)
        return False

    # Fill password
    try:
        pwd_loc = page.locator('[name="password"], #password, input[type="password"]')
        pwd_loc.first.wait_for(state="visible")
        pwd_loc.first.fill(password)
    except Exception as e:
        print(f"  ❌ Login: password field not found — {e}", flush=True)
        return False

    # Submit — cover button label variants used across OpenShift versions
    try:
        submit_loc = page.locator(
            '[type="submit"], '
            'button:text-is("Log in"), button:text-is("Login"), '
            'button:text-is("Sign in"), button:text-is("Sign In")'
        )
        submit_loc.first.wait_for(state="visible")
        submit_loc.first.click()
    except Exception as e:
        print(f"  ❌ Login: submit button not found — {e}", flush=True)
        return False

    # Wait for redirect away from all auth pages
    try:
        page.wait_for_function(
            "() => !window.location.href.includes('/oauth/') && "
            "!window.location.href.includes('/login') && "
            "document.body.innerText.trim().length > 50",
            timeout=timeout,
        )
    except Exception:
        pass

    final = page.url
    failed = any(p in final.lower() for p in
                 ("login", "oauth/authorize", "access_denied"))
    if failed:
        print(f"  ❌ Login: ended at {final}", flush=True)
        try:
            snippet = page.inner_text("body")[:200].replace("\n", " ").strip()
            print(f"     Page: {snippet}", flush=True)
        except Exception:
            pass
    return not failed
