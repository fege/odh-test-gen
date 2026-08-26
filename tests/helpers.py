"""Shared test helper functions."""

import json
from pathlib import Path

from scripts.utils.frontmatter_utils import write_frontmatter
from scripts.utils.schemas import TEMPLATE_HEADINGS
from tests.consts.test_plan_constants import TESTPLAN_VALID_BODY, VALID_TEST_PLAN_DATA
from tests.consts.validation_constants import NON_UTF8_PLAN_BYTES


def write_valid_testplan(path, **frontmatter_overrides):
    """Write a TestPlan.md with validated frontmatter and proper structure.

    Extra keyword arguments are merged into VALID_TEST_PLAN_DATA (e.g. components=[...]).
    """
    Path(path).write_text(TESTPLAN_VALID_BODY)
    write_frontmatter(str(path), {**VALID_TEST_PLAN_DATA, **frontmatter_overrides}, "test-plan")


def write_tc(tc_dir, tc_id, automation_status="Not Started", status=None):
    """Write a minimal TC-*.md whose frontmatter is enough for filter_test_cases."""
    path = Path(tc_dir) / f"{tc_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"test_case_id: {tc_id}"]
    if status is not None:
        lines.append(f"status: {status}")
    lines.append(f"automation_status: {automation_status}")
    lines.append("---\n")
    path.write_text("\n".join(lines))
    return path


def write_testplan_with_objectives(path, objectives_body):
    """Write a minimal TestPlan.md whose Section 1.3 holds the given objective lines.

    Uses TEMPLATE_HEADINGS (parsed from the real production template) for the heading, so this
    stays correct if the template's Section 1.3 heading text ever changes.
    """
    Path(path).write_text(f"---\nfeature: Test\n---\n\n{TEMPLATE_HEADINGS['1.3']}\n\n{objectives_body}")
    return str(path)


def objectives_citing_every_ac(ac_count, nfr_categories):
    """Build a Section 1.3 objectives body with one numbered objective citing each AC 1..ac_count,
    followed by one objective per NFR category — the shape a correctly-behaving analyzer produces.
    """
    lines = [f"{n}. Verify AC {n} (AC: #{n} — placeholder text)" for n in range(1, ac_count + 1)]
    lines.extend(
        f"{i}. Verify {category} (NFR: {category} — placeholder text)"
        for i, category in enumerate(nfr_categories, start=ac_count + 1)
    )
    return "\n".join(lines) + "\n"


def build_review_payload(
    scores,
    score=None,
    verdict="Ready",
    passed=True,
    before_score=None,
    before_scores=None,
    feature="Test",
    source_key="RHAISTRAT-1",
    last_updated="2026-08-06",
):
    """Build a test-plan-review frontmatter payload dict from scores/verdict."""
    data = {
        "feature": feature,
        "source_key": source_key,
        "score": score if score is not None else sum(scores.values()),
        "pass": passed,
        "verdict": verdict,
        "scores": scores,
        "auto_revised": False,
        "last_updated": last_updated,
    }
    if before_score is not None:
        data["before_score"] = before_score
        data["before_scores"] = before_scores or dict(scores)
    return data


def add_feature(repo_path, feature_name, files):
    """Add a feature directory with specified files to a repo."""
    feature = Path(repo_path) / feature_name
    feature.mkdir(parents=True)
    for f in files:
        p = feature / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {f}\n")


def strat_with_testability_heading(heading: str) -> str:
    """Build a minimal STRAT string whose Testability(-ish) section uses the given heading.

    Produces 2 main ACs under 'h3. Acceptance Criteria' and one distinctive bullet
    under the caller-supplied heading.  The word 'throttled' appears only in that
    Testability bullet, so callers can assert its presence or absence in AC texts
    without full-text parsing.  A trailing 'h3. Effort Estimate' bounds the section
    so extract_jira_section terminates it correctly.
    """
    return (
        "h3. Acceptance Criteria\n\n"
        "# *Login works*: Given valid creds When submitted Then access granted\n"
        "# *Logout works*: Given a session When user logs out Then session ends\n\n"
        f"{heading}\n\n"
        "# *Rate limit*: Given many attempts When threshold hit Then requests are throttled\n\n"
        "h3. Effort Estimate\n\n(bounds the section)\n"
    )


def setup_validation_config(base_dir, core_config, team_configs=None, config_filename="scope_patterns.json"):
    """Setup validation config files for testing.

    Args:
        base_dir: Base path (typically tmp_path from pytest fixture)
        core_config: Core config dict to write to checks/core/{config_filename}
        team_configs: Optional dict of {team_name: config_dict}
        config_filename: Config filename (scope_patterns.json or boilerplate_patterns.json)

    Returns:
        str: Path to checks directory
    """
    checks_dir = Path(base_dir) / "checks"
    (checks_dir / "core").mkdir(parents=True, exist_ok=True)
    (checks_dir / "core" / config_filename).write_text(json.dumps(core_config))

    if team_configs:
        for team_name, config in team_configs.items():
            (checks_dir / team_name).mkdir(parents=True, exist_ok=True)
            (checks_dir / team_name / config_filename).write_text(json.dumps(config))

    return str(checks_dir)


def setup_calibration_dir(base_dir, core_files, team_files=None):
    """Write a calibration/ tree (core/ plus optional extra dirs) under base_dir.

    Extra directories (reserved ``ui/`` overlay or COMPONENT teams) are written the same
    way via ``team_files``, e.g. ``{"ui": {filename: content}, "ai_hub": {...}}``.

    Args:
        base_dir: Base path (typically tmp_path from pytest)
        core_files: Mapping of filename -> text content under calibration/core/
        team_files: Optional mapping of directory name -> {filename: content}

    Returns:
        str: Path to the calibration directory
    """
    calibration_dir = Path(base_dir) / "calibration"
    (calibration_dir / "core").mkdir(parents=True, exist_ok=True)
    for name, content in core_files.items():
        (calibration_dir / "core" / name).write_text(content)
    if team_files:
        for dir_name, files in team_files.items():
            extra_dir = calibration_dir / dir_name
            extra_dir.mkdir(parents=True, exist_ok=True)
            for name, content in files.items():
                (extra_dir / name).write_text(content)
    return str(calibration_dir)


def make_unreadable_test_plan_path(base_dir, kind):
    """Return a test_plan_path that exists but cannot be read as UTF-8 text.

    kind "directory": path is a directory (IsADirectoryError from Path.read_text).
    kind "non_utf8": file whose bytes are not valid UTF-8 (UnicodeDecodeError).
    """
    base = Path(base_dir)
    if kind == "directory":
        path = base / "as_directory"
        path.mkdir()
        return str(path)
    if kind == "non_utf8":
        path = base / "TestPlan.md"
        path.write_bytes(NON_UTF8_PLAN_BYTES)
        return str(path)
    raise ValueError(f"unknown unreadable plan kind: {kind}")
