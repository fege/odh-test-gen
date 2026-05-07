#!/usr/bin/env python3
"""
ui_prepare.py — Deterministic setup for test-plan.ui-verify.

Handles all deterministic phases (prerequisites, TC loading, credential
resolution, URL resolution, cluster snapshot) and writes a context file
that the Claude skill reads to skip setup and jump straight to TC execution.

Usage:
    python3 ui_prepare.py --test-plan-pr https://github.com/fege/test-plan/pull/5
    python3 ui_prepare.py --test-plan-pr <url> --tc TC-FILTER --priority P0
    python3 ui_prepare.py --test-plan fege/test-plan/tool_calling_model_catalog   # reads from main
    python3 ui_prepare.py --target-url https://... --test-plan-pr <url>
    python3 ui_prepare.py --setup
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required. Run: pip install pyyaml")
    sys.exit(1)

from paths import SKILL_DIR, TMP_DIR  # defined once in paths.py
from browser_common import do_oauth_login  # scripts/ is a package; import works directly
from helpers import is_ui_test as _is_ui_test, matches_tc_filter as _matches_tc_filter
from github_utils import fetch_meta, fetch_tc_files


def _ensure_repo_on_path() -> None:
    """Add the repo's top-level scripts/ to sys.path (idempotent, no side effects at import time)."""
    _git = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, cwd=str(SKILL_DIR),
    )
    if _git.returncode == 0 and _git.stdout.strip():
        _repo_scripts = os.path.join(_git.stdout.strip(), "scripts")
        if _repo_scripts not in sys.path:
            sys.path.insert(0, _repo_scripts)

CONTEXT    = TMP_DIR / "ui_context.json"
TV_FILE    = SKILL_DIR / "test-variables.yml"
TV_EXAMPLE = SKILL_DIR / "test-variables.yml.example"
REGISTRY   = SKILL_DIR / "component-registry.yaml"



# ── helpers ──────────────────────────────────────────────────────────────────

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def _load_tv(upgrade_phase: str = "") -> dict:
    """Load test-variables.yml and merge upgrade_clusters.<phase> profile if present.

    The upgrade_clusters.<phase> section overrides only the keys it specifies;
    everything else inherits from the top-level defaults. This allows a single
    test-variables.yml to hold both cluster configs without editing between runs.
    """
    if not TV_FILE.exists():
        return {}
    tv = yaml.safe_load(TV_FILE.read_text()) or {}
    if not upgrade_phase:
        return tv
    profile = (tv.get("upgrade_clusters") or {}).get(upgrade_phase, {})
    if not profile:
        return tv
    merged = dict(tv)
    for key, val in profile.items():
        if key == "admin_user" and isinstance(val, dict) and isinstance(merged.get("admin_user"), dict):
            merged["admin_user"] = {**merged["admin_user"], **val}
        else:
            merged[key] = val
    return merged


def fail(msg):
    print(f"\n❌ {msg}", file=sys.stderr)
    sys.exit(1)


def section(title):
    print(f"\n{'─'*60}\n  {title}\n{'─'*60}")


def _atexit_kill_browser(pid: int) -> None:
    """Safety-net: kill the browser if this process exits before Claude's Phase 3 cleanup."""
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass  # already stopped — no-op


# ── Phase 0: prerequisites ────────────────────────────────────────────────────

def phase0_preflight():
    section("Phase 0: Prerequisites")

    # Clear stale runtime files and kill any orphaned browser from previous run
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    ctx_path = TMP_DIR / "ui_context.json"
    if ctx_path.exists():
        try:
            old_ctx = json.loads(ctx_path.read_text())
            old_pid = old_ctx.get("browser_pid")
            if old_pid:
                import os as _os, signal as _sig
                try:
                    _os.kill(old_pid, _sig.SIGTERM)
                    print(f"  Stopped previous browser (pid={old_pid})")
                except ProcessLookupError:
                    pass
        except Exception:
            pass
    for f in TMP_DIR.iterdir():
        # is_dir() follows symlinks — use is_symlink() to catch .ui-session (symlink → dir)
        if not f.is_dir() or f.is_symlink():
            f.unlink(missing_ok=True)

    # Syntax-check all scripts before doing anything else
    import py_compile
    scripts_ok = True
    for script in sorted((SKILL_DIR / "scripts").glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as e:
            print(f"  ❌ syntax error in {script.name}: {e}")
            scripts_ok = False
    if not scripts_ok:
        fail("Script syntax errors found — fix them before running.")

    missing = []

    # Check playwright Python package
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        print(f"  ✅ {'playwright':<20} Python API")
    except ImportError:
        print(f"  ❌ {'playwright':<20} not found — run: pip install playwright && playwright install chromium")
        missing.append("playwright")

    install_hints = {
        "gh": "brew install gh  →  then: gh auth login",
    }
    required = [
        ("gh", ["gh", "auth", "status"]),
    ]
    for name, cmd in required:
        r = run(cmd)
        if r.returncode == 0:
            ver = r.stdout.splitlines()[0] if r.stdout else "ok"
            print(f"  ✅ {name:<20} {ver}")
        else:
            # gh specifically: distinguish not-installed vs not-authenticated
            if name == "gh" and run(["gh", "--version"]).returncode == 0:
                print(f"  ❌ {name:<20} installed but not authenticated — run: gh auth login")
            else:
                print(f"  ❌ {name:<20} not found — install: {install_hints[name]}")
            missing.append(name)


    oc_r = run(["oc", "version", "--client"])
    if oc_r.returncode == 0:
        print(f"  ✅ oc                   found")
    else:
        print(f"  ⚠️  oc                   not found — URL must be provided manually, no cluster snapshot")

    if missing:
        fail(f"Required tools missing: {', '.join(missing)}\n  See install hints above.")

    print(f"\n  SKILL_DIR: {SKILL_DIR}")
    return {
        "skill_dir":        str(SKILL_DIR),
        "oc_available":     oc_r.returncode == 0,
    }


# ── Phase 1: TC loading ───────────────────────────────────────────────────────

def phase1_load_tcs(args):
    section("Phase 1: Load Test Plan")

    import tempfile
    _ensure_repo_on_path()
    from utils.tc_parser import parse_tc_file
    from utils.frontmatter_utils import read_frontmatter

    tc_patterns = [p.strip() for p in args.tc.split(",") if p.strip()] if args.tc else []

    # ── Determine source ──────────────────────────────────────────────────────
    if args.test_plan_pr:
        m = re.search(r'/pull/(\d+)', args.test_plan_pr)
        if not m:
            fail(f"Cannot parse PR number from: {args.test_plan_pr}")
        pr_number = int(m.group(1))
        repo_m = re.search(r'github\.com/([^/]+/[^/]+)/pull', args.test_plan_pr)
        repo = repo_m.group(1) if repo_m else "fege/collection-tests" 
        # Get PR head SHA and feature directory from PR files
        ref_r = run(["gh", "api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".head.sha"])
        ref = ref_r.stdout.strip() if ref_r.returncode == 0 and ref_r.stdout.strip() else "main"
        feat_r = run(["gh", "api", f"repos/{repo}/pulls/{pr_number}/files",                                                                                                                                                
                "--jq", '[.[].filename | select(contains("/test_cases/")) | split("/test_cases/")[0]] | unique | .[0]'])
        feature = feat_r.stdout.strip() if feat_r.returncode == 0 else ""
        if not feature:
            fail("Could not detect feature directory from PR files.")
    elif args.test_plan:
        parts = args.test_plan.split("/")
        repo = "/".join(parts[:2])
        feature = "/".join(parts[2:])
        ref = "main"
    elif args.jira:
        fail("--jira mode is not yet implemented.\n"
             "  Use --test-plan-pr or --test-plan to load TCs from fege/test-plan.")
    else:
        fail("No input mode specified. Use --test-plan-pr, --test-plan, or --jira.")

    meta = fetch_meta(repo, feature, ref)
    try:
        raw_files = fetch_tc_files(repo, feature, ref, tc_patterns)
    except RuntimeError as e:
        fail(str(e))

    # ── Parse using shared utils, writing fetched content to temp files ───────
    test_cases = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for filename, content in raw_files:
            tmppath = Path(tmpdir) / filename
            tmppath.write_text(content, encoding="utf-8")

            # Extract H1 title before sections are parsed (tc_parser drops it)
            title_m = re.search(r'^# (.+)$', content, re.MULTILINE)
            title = title_m.group(1).strip() if title_m else filename.replace(".md", "")

            try:
                data = parse_tc_file(str(tmppath), read_frontmatter)
            except Exception as e:
                print(f"  ⚠️  Skipping {filename}: {e}", flush=True)
                continue

            tc_id = data.get("test_case_id", filename.replace(".md", ""))
            steps = data.get("test_steps", [])

            # Filter: explicit patterns override UI keyword detection
            if tc_patterns:
                if not _matches_tc_filter(tc_id, tc_patterns):
                    continue
            elif not _is_ui_test(steps):
                continue

            if args.priority and data.get("priority", "") != args.priority:
                continue
            if data.get("status", "") in {"Blocked", "Out of Scope", "Deprecated"}:
                continue

            obj = data.get("objective", "")
            first = obj.split(".")[0].strip() if obj else ""
            obj_short = (first[:120].rsplit(" ", 1)[0] + "…") if len(first) > 120 else first

            test_cases.append({
                "id":               tc_id,
                "title":            title,
                "priority":         data.get("priority", "P0"),
                "status":           data.get("status", "Draft"),
                "strat_key":        data.get("strat_key", meta.get("strat_key", "")),
                "objective":        obj,
                "objective_short":  obj_short,
                "preconditions":    data.get("preconditions", []),
                "steps":            steps,
                "expected_results": data.get("expected_results", []),
                "notes":            data.get("body", ""),
                "has_ui_steps":     _is_ui_test(steps),
                "step_count":       len(steps),
                "upgrade_phase":    data.get("upgrade_phase", ""),
            })

    plan = {
        "feature":   meta.get("feature", feature),
        "strat_key": meta.get("strat_key", ""),
        "test_cases": test_cases,
    }
    tcs = plan.get("test_cases", [])

    # Filter by upgrade phase when --upgrade-phase is set.
    # pre: include TCs with upgrade_phase "pre", "both", or unset (regressions always run)
    # post: include TCs with upgrade_phase "post", "both", or unset
    if getattr(args, "upgrade_phase", ""):
        phase = args.upgrade_phase
        tcs = [tc for tc in tcs if tc.get("upgrade_phase", "") in (phase, "both", "")]
        plan["test_cases"] = tcs
        if phase == "pre":
            print(f"\n  ⬆  Upgrade mode — PRE-UPGRADE baseline run (phase: pre)")
        else:
            print(f"\n  ⬆  Upgrade mode — POST-UPGRADE verification run (phase: post)")

    print(f"\n  Feature:  {plan.get('feature', '?')}")
    print(f"  Strategy: {plan.get('strat_key', '?')}")
    print(f"  TCs:      {len(tcs)}")

    non_ui = []
    for tc in tcs:
        ui_flag = "" if tc.get("has_ui_steps", True) else "  ⚠️  no UI steps"
        steps = tc.get("step_count", 0)
        obj   = tc.get("objective_short", "")
        print(f"    {tc['id']:<15} {tc['priority']}  {tc['title']}{ui_flag}")
        if obj:
            print(f"    {'':15}       └─ {obj}")
        if steps:
            print(f"    {'':15}          {steps} steps")
        if not tc.get("has_ui_steps", True):
            non_ui.append(tc["id"])

    if not tcs:
        fail("No test cases matched the filter.")

    if non_ui:
        print(f"\n  ⚠️  {len(non_ui)} TC(s) have no browser UI steps and will be BLOCKED:")
        for tc_id in non_ui:
            print(f"       {tc_id} — not verifiable via browser")
        print("  These were explicitly requested via --tc. Remove them or proceed knowing they will be BLOCKED.")

    # Approval gate
    print()
    if args.priority and not args.tc:
        print(f"  Tip: --priority {args.priority} requires fetching all files to read frontmatter.")
        print(f"       Add --tc <category> to reduce fetches (e.g. --tc TC-E2E --priority {args.priority})")
    elif not args.tc:
        print("  Tip: use --tc <ID> or <category> to narrow (e.g. --tc TC-E2E-003 or --tc TC-E2E)")

    ans = input("Proceed? [Enter = all / n = abort / TC IDs = subset, e.g. TC-UI-001,TC-UI-002]: ").strip()

    if ans.lower() == "n":
        print("Aborted.")
        sys.exit(0)

    if ans and ans.lower() not in ("y", "yes"):
        # Treat input as a subset of TC IDs
        requested = {x.strip() for x in ans.replace(",", " ").split() if x.strip()}
        available  = {tc["id"] for tc in tcs}
        not_found  = requested - available
        if not_found:
            print(f"  ⚠️  Not in plan: {', '.join(sorted(not_found))} — ignored")
        tcs = [tc for tc in tcs if tc["id"] in requested]
        if not tcs:
            fail("No matching TCs in subset — aborting.")
        print(f"  Running subset: {', '.join(tc['id'] for tc in tcs)}")
        plan["test_cases"] = tcs

    return plan


# ── Phase 2: component resolution ────────────────────────────────────────────

def phase2_component(plan, args):
    section("Phase 2: Component Resolution")

    if not REGISTRY.exists():
        fail(f"Component registry not found: {REGISTRY}\n  Make sure the skill is fully installed.")
    with open(REGISTRY) as f:
        registry = yaml.safe_load(f) or {}
    if "components" not in registry:
        fail(f"component-registry.yaml is missing 'components' key: {REGISTRY}")

    # Build keyword map from registry
    scores = {}
    all_text = ""
    if plan:
        for tc in plan.get("test_cases", []):
            all_text += f" {tc.get('title','')} {' '.join(tc.get('steps',[]))}"
    all_text = all_text.lower()

    for key, cfg in registry["components"].items():
        keywords = cfg.get("keywords", [])
        score = sum(1 for kw in keywords if kw.lower() in all_text)
        if score:
            scores[key] = score

    if scores:
        component = max(scores, key=scores.get)
        print(f"  Matched: {component} (score={scores[component]})")
    else:
        component = "odh-dashboard"
        print(f"  No keyword match in TC text.")
        ans = input(f"  Defaulting to odh-dashboard — is this correct? [Y/n]: ").strip().lower()
        if ans == "n":
            choices = list(registry["components"].keys())
            for i, k in enumerate(choices):
                print(f"    {i+1}. {k}")
            sel = input("  Enter number: ").strip()
            try:
                component = choices[int(sel) - 1]
            except (ValueError, IndexError):
                fail("Invalid selection.")

    cfg = registry["components"][component]
    print(f"  Config: {cfg['description']}")
    return component, cfg


# ── Phase 3: URL resolution ───────────────────────────────────────────────────

def phase3_url(component_cfg, args):
    section("Phase 3: Target URL Resolution")

    # 1. Explicit flag
    if args.target_url:
        print(f"  Using --target-url: {args.target_url}")
        return args.target_url

    # 2. Env var
    env_url = os.environ.get("ODH_QA_TARGET_URL", "")
    if env_url:
        print(f"  Using ODH_QA_TARGET_URL: {env_url}")
        return env_url

    # 3. test-variables.yml target_url (merged with upgrade_clusters profile if set)
    if TV_FILE.exists():
        tv = _load_tv(getattr(args, "upgrade_phase", ""))
        tv_url = tv.get("target_url", "")
        if tv_url and "example.com" not in tv_url:
            print(f"  Using target_url from test-variables.yml: {tv_url}")
            return tv_url

    # 3. oc get route (only if oc is available)
    if not run(["oc", "version", "--client"]).returncode == 0:
        print("  oc not available — skipping route lookup.")
        print("  Could not resolve URL automatically.")
        url = input("  Enter dashboard URL: ").strip()
        if not url:
            fail("No URL provided.")
        return url

    route_names = component_cfg.get("url_resolution", {}).get("route_names", ["data-science-gateway"])
    namespaces  = component_cfg.get("url_resolution", {}).get("namespace_candidates",
                                    ["openshift-ingress", "redhat-ods-applications", "opendatahub"])

    for route in route_names:
        for ns in namespaces:
            r = run(["oc", "get", "route", route, "-n", ns,
                     "-o", "jsonpath={.spec.host}"])
            if r.returncode == 0 and r.stdout.strip():
                url = f"https://{r.stdout.strip()}"
                print(f"  Found route: {url}  (route={route} ns={ns})")
                return url

    # 4. Prompt — with diagnostic hint and example
    diag = run(["oc", "cluster-info"])
    if diag.returncode == 0:
        print(f"  Cluster info: {diag.stdout.splitlines()[0].strip()}")
    else:
        print("  Hint: check oc login — you may not be connected to a cluster.")
    print("  Could not resolve URL from routes. Enter it manually.")
    url = input("  Dashboard URL (e.g. https://rh-ai.apps.my-cluster.example.com): ").strip()
    if not url:
        fail("No URL provided.")
    return url


# ── Phase 4: credentials ──────────────────────────────────────────────────────

def _tv_field_error(field: str, hint: str = "") -> None:
    """Fail with a clear message pointing to the exact field in test-variables.yml."""
    msg = (f"'{field}' is not set in test-variables.yml\n"
           f"  Edit: {TV_FILE}\n"
           f"  Template: {TV_EXAMPLE}")
    if hint:
        msg += f"\n  Hint: {hint}"
    fail(msg)


def phase4_credentials(cluster_api, args):
    section("Phase 4: Credential Resolution")

    # ── Priority 1: environment variables (CI) ────────────────────────────────
    username = os.environ.get("ODH_QA_USERNAME", "")
    password = os.environ.get("ODH_QA_PASSWORD", "")
    idp      = os.environ.get("ODH_QA_IDP", "")
    oc_token = os.environ.get("ODH_QA_OC_TOKEN", "")
    if not cluster_api:
        cluster_api = os.environ.get("ODH_QA_CLUSTER_API", "")

    # ── Priority 2: test-variables.yml ───────────────────────────────────────
    tv = {}
    if TV_FILE.exists():
        tv = _load_tv(getattr(args, "upgrade_phase", ""))
        print(f"  Reading: {TV_FILE}")
    else:
        # Only fail here if env vars are also missing — CI may not need the file
        if not (username and password and idp):
            fail(f"test-variables.yml not found.\n"
                 f"  Copy the template and fill in your values:\n"
                 f"    cp {TV_EXAMPLE} {TV_FILE}\n"
                 f"  Then edit {TV_FILE} with your cluster credentials.")

    admin = tv.get("admin_user", {}) or {}
    username    = username    or admin.get("username", "")
    password    = password    or admin.get("password", "")
    idp         = idp         or tv.get("idp", "")
    oc_token    = oc_token    or tv.get("oc_token", "")
    # cluster_api is optional — auto-detected from target_url or oc session if not provided
    cluster_api = cluster_api or tv.get("cluster_api", "")

    # ── Priority 3: derive cluster API from target_url (apps. → api.) ─────────
    # Works for standard OpenShift clusters: https://X.apps.CLUSTER → https://api.CLUSTER:6443
    if not cluster_api:
        tv_url = tv.get("target_url", "")
        if tv_url:
            m = re.search(r'https?://[^.]+\.apps\.(.+)', tv_url)
            if m:
                cluster_api = f"https://api.{m.group(1)}:6443"
                print(f"  cluster_api derived from target_url: {cluster_api}")

    # ── Priority 4: fall back to active oc session ────────────────────────────
    if not cluster_api:
        r = run(["oc", "config", "view", "--minify",
                 "-o", "jsonpath={.clusters[0].cluster.server}"])
        cluster_api = r.stdout.strip()
        if cluster_api:
            print(f"  cluster_api from oc config: {cluster_api}")

    # ── Validate — fail clearly, no interactive prompts ───────────────────────
    PLACEHOLDER = "your-password-here"

    if not cluster_api:
        fail(
            "Could not determine cluster API URL.\n"
            "  Tried: target_url derivation (apps.X → api.X), oc config, ODH_QA_CLUSTER_API env.\n"
            "  Make sure you are logged in via 'oc login' or set ODH_QA_CLUSTER_API."
        )

    if not username:
        _tv_field_error("admin_user.username", "e.g. ldap-admin1")

    if not password or password == PLACEHOLDER:
        _tv_field_error("admin_user.password",
                        "replace 'your-password-here' with your actual password")

    if not idp:
        _tv_field_error("idp",
                        "check the OpenShift login page — common values: "
                        "ldap-provider-qe, htpasswd-cluster-admin")

    print(f"  Cluster API: {cluster_api}")
    print(f"  IDP:         {idp}")
    print(f"  Username:    {username}")
    print(f"  Password:    SET")

    # ── Quick validation: oc login (pipe password via stdin, never as -p arg) ──
    if cluster_api and not oc_token:
        insecure_tls = tv.get("insecure_tls", False)
        login_cmd = ["oc", "login", cluster_api, f"--username={username}"]
        if insecure_tls:
            login_cmd.append("--insecure-skip-tls-verify=true")
        val = subprocess.run(login_cmd, input=password, capture_output=True, text=True)
        if val.returncode == 0:
            print("  ✅ Credentials validated (oc login succeeded)")
        else:
            fail(f"oc login failed — password may be wrong or expired.\n"
                 f"  Update admin_user.password in {TV_FILE} and re-run.")

    return {
        "cluster_api": cluster_api,
        "oc_token":    oc_token,
        "username":    username,
        "idp":         idp,
        # password intentionally NOT written to context file
        # SKILL reads it directly from test-variables.yml at runtime
    }


# ── Phase 5: cluster snapshot ─────────────────────────────────────────────────

def phase5_snapshot(oc_available):
    section("Phase 5: Pre-Test Snapshot")

    pre_projects = set()
    if oc_available:
        # Show cluster so user can confirm they're on the right one
        whoami_r = run(["oc", "whoami", "--show-server"])
        server = whoami_r.stdout.strip() if whoami_r.returncode == 0 else "unknown"
        user_r = run(["oc", "whoami"])
        user = user_r.stdout.strip() if user_r.returncode == 0 else "unknown"
        print(f"  Cluster: {server}  (user: {user})")

        r = run(["oc", "get", "projects", "--no-headers",
                 "-o", "custom-columns=NAME:.metadata.name"])
        if r.returncode == 0:
            pre_projects = set(r.stdout.strip().splitlines())
            (TMP_DIR / "ui-existing-projects.txt").write_text(
                "\n".join(sorted(pre_projects)) + "\n"
            )
            print(f"  Recorded {len(pre_projects)} existing projects")

    (TMP_DIR / "ui-cleanup-manifest.txt").write_text("# ui-verify cleanup manifest\n")
    return sorted(pre_projects)


# ── Phase 6: prerequisite setup ───────────────────────────────────────────────

def phase6_prerequisites(plan, oc_available, upgrade_phase=""):
    section("Phase 6: Prerequisite Setup")

    if not plan:
        print("  No test plan — skipping.")
        return

    # Collect unique preconditions across all TCs
    seen = set()
    for tc in plan.get("test_cases", []):
        for pre in tc.get("preconditions", []):
            seen.add(pre)

    if not seen:
        print("  No cluster prerequisites required.")
        return

    if not oc_available:
        print("  ⚠️  oc not available — prerequisites must be created manually before continuing.")
        input("  Press Enter when prerequisites are ready, or Ctrl+C to abort: ")
        return

    # Only create resources for well-known types we can automate
    # (others require manual setup and will be flagged to the user)
    suffix = str(int(time.time()))[-6:]
    manual = []
    for pre in seen:
        pl = pre.lower()
        # Only auto-create a project for generic preconditions ("a new project",
        # "fresh namespace"). Skip when the precondition names a specific namespace
        # (backtick-quoted or otherwise) — that namespace must be pre-provisioned.
        names_specific = "`" in pre or any(
            kw in pl for kw in ("in namespace", "in project", "namespace `", "project `")
        )
        if ("openshift project" in pl or "namespace" in pl) and not names_specific:
            name = f"qa-uiv-{suffix}"
            r = run(["oc", "new-project", name])
            if r.returncode == 0:
                print(f"  ✅ Created project: {name}")
                with open(str(TMP_DIR / "ui-cleanup-manifest.txt"), "a") as f:
                    f.write(f"project: {name}\n")
            else:
                print(f"  ⚠️  Could not create project: {r.stderr.strip()}")
        else:
            manual.append(pre)

    if manual:
        print()
        print("  ┌─────────────────────────────────────────────────────┐")
        print("  │  ⚠️  MANUAL SETUP REQUIRED before proceeding         │")
        print("  └─────────────────────────────────────────────────────┘")
        for pre in manual:
            print(f"    • {pre}")
        if upgrade_phase:
            print()
            print("  ℹ️  Upgrade test: resources you create for this test will NOT")
            print("     be cleaned up automatically — you need them to persist")
            print("     through the upgrade cycle. Delete them manually when done.")
        print()
        ans = input("  Confirm all of the above are ready? [y/N]: ").strip().lower()
        if ans != "y":
            print("  Aborted — set up the prerequisites and re-run.")
            sys.exit(0)


# ── Session setup ─────────────────────────────────────────────────────────────

def setup_session(feature_name):
    session_name = f"uiv-{feature_name}-{int(time.time())}"
    session_dir = SKILL_DIR / "results" / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    # Symlink inside .tmp/ so SKILL.md has a stable relative-to-skill path
    link = TMP_DIR / ".ui-session"
    try:
        link.unlink()
    except FileNotFoundError:
        pass
    link.symlink_to(session_dir.resolve())
    return str(session_dir)


# ── Browser launch + login ────────────────────────────────────────────────────

def launch_browser(target_url: str, tv: dict) -> dict:
    """Start a persistent Chromium browser via CDP, log in, and return connection info."""
    import subprocess as _sp
    from playwright.sync_api import sync_playwright

    section("Phase 7: Browser Launch & Login")

    # Get Playwright's bundled Chromium path
    with sync_playwright() as p:
        chromium_path = p.chromium.executable_path

    # Launch Chromium with CDP on a random free port, bound to localhost only.
    # --remote-debugging-address=127.0.0.1 prevents the debug port from binding
    # on 0.0.0.0 (all interfaces), which would allow anyone on the same network
    # to connect to the authenticated browser session.
    proc = _sp.Popen(
        [chromium_path,
         "--headless=new",
         "--remote-debugging-port=0",          # OS picks free port
         "--remote-debugging-address=127.0.0.1",  # localhost only — security
         "--ignore-certificate-errors",
         "--window-size=1920,1080",
         "--no-first-run",
         "--no-default-browser-check"],
        stdout=_sp.DEVNULL, stderr=_sp.PIPE, text=True,
        start_new_session=True,
    )

    # Read CDP endpoint from stderr (Chrome prints "DevTools listening on ws://...")
    import re as _re
    cdp_url = None
    deadline = time.time() + 10
    while time.time() < deadline:
        line = proc.stderr.readline()
        if not line:
            time.sleep(0.1)
            continue
        m = _re.search(r'DevTools listening on (ws://[^\s]+)', line)
        if m:
            ws = m.group(1)
            # Convert ws://127.0.0.1:PORT/... → http://127.0.0.1:PORT
            port_m = _re.search(r':(\d+)/', ws)
            if port_m:
                cdp_url = f"http://127.0.0.1:{port_m.group(1)}"
            break

    if not cdp_url:
        proc.kill()
        fail("Browser failed to start — check: pip install playwright && playwright install chromium")

    print(f"  Browser running  (pid={proc.pid}, cdp={cdp_url})")

    # Login via Playwright Python API
    admin = tv.get("admin_user", {}) or {}
    username = admin.get("username", "")
    password = admin.get("password", "")
    idp      = tv.get("idp", "")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        ctx_b   = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
        )
        page = ctx_b.new_page()

        print(f"  Navigating to:   {target_url}")
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=15000)

        ok = do_oauth_login(page, username, password, idp, timeout=30000)
        if not ok:
            proc.kill()
            fail("Login failed — check credentials in test-variables.yml or verify the cluster is reachable")

        print(f"  ✅ Logged in     ({page.url[:60]})")
        # exit with block — browser subprocess keeps running

    return {"browser_cdp": cdp_url, "browser_pid": proc.pid}


# ── Write context ─────────────────────────────────────────────────────────────

def write_context(ctx):
    CONTEXT.write_text(json.dumps(ctx, indent=2))
    print(f"\n  Context written: {CONTEXT}")


# ── --setup mode ──────────────────────────────────────────────────────────────

def setup_mode():
    r = run(["oc", "config", "view", "--minify",
             "-o", "jsonpath={.clusters[0].cluster.server}"])
    cluster_api = r.stdout.strip()
    oc_user_r = run(["oc", "whoami"])
    username = oc_user_r.stdout.strip()

    print(f"""
test-plan.ui-verify setup
========================

To configure credentials, copy the template and edit it:

  cp {TV_EXAMPLE} {TV_FILE}

Then fill in these fields in test-variables.yml:

  cluster_api:  {cluster_api or 'https://api.my-cluster.example.com:6443'}
  idp:          <identity provider shown on the OpenShift login page>
  admin_user:
    username:   {username or 'ldap-admin1'}
    password:   <your password>

test-variables.yml is gitignored — it will never be committed.
""")
    sys.exit(0)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--test-plan-pr",   metavar="URL")
    parser.add_argument("--test-plan",      metavar="PATH")
    parser.add_argument("--jira",           metavar="KEY")
    parser.add_argument("--pr",             metavar="URL",  help="Component PR URL")
    parser.add_argument("--target-url",     metavar="URL")
    parser.add_argument("--tc",       default="",
                        help="Comma-separated TC filter: exact IDs (TC-E2E-001) or "
                             "category prefixes (TC-E2E, TC-FILTER). Default: all UI-capable TCs.")
    parser.add_argument("--priority", default="",
                        help="Filter by priority: P0, P1, P2. Default: all priorities.")
    parser.add_argument("--setup",          action="store_true")
    parser.add_argument("--upgrade-phase",  choices=["pre", "post"], default="",
                        help="Upgrade testing mode. 'pre': run pre-upgrade TCs and save baseline. "
                             "'post': run post-upgrade TCs and generate comparison report against baseline.")
    parser.add_argument("--baseline",        metavar="SESSION_DIR", default="",
                        help="Explicit baseline session directory for --upgrade-phase post. "
                             "Overrides the auto-detected upgrade-baseline.json pointer. "
                             "Use to compare a post run against any prior session (e.g. the original "
                             "2.x PASS state when verifying a fix after a broken intermediate state).")
    parser.add_argument("--refresh-map",    metavar="PATH",
                        help="Regenerate element-map.yaml from the given odh-dashboard source path, then exit. "
                             "Example: --refresh-map /path/to/odh-dashboard")
    args = parser.parse_args()

    if args.setup:
        setup_mode()

    if args.refresh_map:
        section("Refreshing element map")
        r = subprocess.run(
            [sys.executable,
             str(SKILL_DIR / "scripts" / "build_element_map.py"),
             "--source", args.refresh_map,
             "--out", str(SKILL_DIR / "element-map.yaml")],
        )
        sys.exit(r.returncode)

    print("\n🚀 test-plan.ui-verify — preparation phase")

    # When --baseline is set and no --tc filter was given, automatically use
    # the same TCs that were run in the baseline so the comparison is consistent.
    if args.baseline and not args.tc:
        _bl_log = Path(args.baseline) / "tc_log.json"
        if _bl_log.exists():
            _bl_ids = list(json.loads(_bl_log.read_text()).keys())
            if _bl_ids:
                args.tc = ",".join(_bl_ids)
                print(f"  ℹ️  Auto-selected TCs from baseline: {args.tc}")

    info        = phase0_preflight()
    plan        = phase1_load_tcs(args)
    component, cfg = phase2_component(plan, args)
    target_url  = phase3_url(cfg, args)
    cluster_api = os.environ.get("ODH_QA_CLUSTER_API", "")
    creds       = phase4_credentials(cluster_api, args)
    pre_projects = phase5_snapshot(info["oc_available"])
    phase6_prerequisites(plan, info["oc_available"], args.upgrade_phase)

    feature_name = (plan or {}).get("feature", "session")
    session_dir  = setup_session(feature_name)

    # Phase 7: Launch persistent browser and log in
    tv = _load_tv(getattr(args, "upgrade_phase", "")) if TV_FILE.exists() else {}
    browser_info = launch_browser(target_url, tv)

    ctx = {
        "skill_dir":     info["skill_dir"],
        "session_dir":   session_dir,
        "target_url":    target_url,
        "cluster_api":   creds["cluster_api"],
        "oc_token":      creds["oc_token"],
        "username":      creds["username"],
        "idp":           creds["idp"],
        "component":     component,
        "feature":       feature_name,
        "strat_key":     (plan or {}).get("strat_key", ""),
        "jira_key":      args.jira or "",
        "source":        (
            f"PR #{args.test_plan_pr.split('/')[-1]} ({args.test_plan_pr})" if args.test_plan_pr
            else args.test_plan or args.jira or "local"
        ),
        "test_cases":    (plan or {}).get("test_cases", []),
        "known_routes":  cfg.get("known_routes", {}),   # from component-registry.yaml — use these first!
        "oc_available":     info["oc_available"],
        "pre_projects":  pre_projects,
        "browser_cdp":   browser_info["browser_cdp"],
        "browser_pid":   browser_info["browser_pid"],
        "prepared_at":   time.strftime("%Y-%m-%dT%H:%M:%S"),
        "upgrade_phase": args.upgrade_phase or "",
        "upgrade_baseline_dir": "",  # filled below for post runs
    }

    # ── Upgrade baseline: save (pre) or load (post) ───────────────────────────
    _baseline_file = SKILL_DIR / ".tmp" / "upgrade-baseline.json"

    if args.upgrade_phase == "pre":
        _baseline_file.parent.mkdir(parents=True, exist_ok=True)
        _baseline_file.write_text(json.dumps({
            "session_dir": session_dir,
            "feature":     feature_name,
            "prepared_at": ctx["prepared_at"],
        }, indent=2))
        print(f"\n  📌 Baseline saved → {_baseline_file}")

    elif args.upgrade_phase == "post":
        if args.baseline:
            # Explicit override — use as-is (supports 3-phase: always compare against phase 1)
            ctx["upgrade_baseline_dir"] = str(Path(args.baseline).resolve())
            print(f"\n  📌 Baseline (explicit) → {ctx['upgrade_baseline_dir']}")
        elif _baseline_file.exists():
            baseline = json.loads(_baseline_file.read_text())
            ctx["upgrade_baseline_dir"] = baseline.get("session_dir", "")
            print(f"\n  📌 Baseline found  → {ctx['upgrade_baseline_dir']}")
            print(f"       (from pre run at {baseline.get('prepared_at', '?')})")
        else:
            print(f"\n  ⚠️  No baseline found at {_baseline_file}")
            print("     Run with --upgrade-phase pre on the old cluster first,")
            print("     or pass --baseline <session-dir> to compare explicitly.")

    write_context(ctx)

    print(f"""
{'='*60}
✅ Preparation complete!

   Feature:    {feature_name}
   Target:     {target_url}
   TCs queued: {len(ctx['test_cases'])}
   Session:    {session_dir}

Now run in Claude Code:

   /test-plan.ui-verify
{'='*60}
{(chr(10) + '  ⬆  After running /test-plan.ui-verify, upgrade the cluster then run:' + chr(10) + '     python3 ui_prepare.py --test-plan-pr <same-url> --upgrade-phase post' + chr(10)) if args.upgrade_phase == 'pre' else ''}""")

    # Launch Claude Code interactively. The user types /test-plan.ui-verify to start.
    # subprocess.run (not os.execlp) keeps this process alive so atexit can
    # kill the browser if Claude crashes before reaching its Phase 3 cleanup.
    import atexit
    import shutil
    browser_pid = browser_info.get("browser_pid")
    if browser_pid:
        atexit.register(lambda pid=browser_pid: _atexit_kill_browser(pid))

    if not shutil.which("claude"):
        print("  claude CLI not found — run /test-plan.ui-verify manually in Claude Code.")
        return

    print("  Launching Claude Code (interactive)...")
    print("  ➜ Type /test-plan.ui-verify to start")
    print("  ➜ Approve permission prompts as they appear — most are one-time\n")
    subprocess.run(["claude"])


if __name__ == "__main__":
    main()
