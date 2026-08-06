"""Shared test helper functions."""

from pathlib import Path

from scripts.utils.frontmatter_utils import write_frontmatter
from scripts.utils.schemas import TEMPLATE_HEADINGS
from tests.constants import TESTPLAN_VALID_BODY, VALID_TEST_PLAN_DATA


def write_valid_testplan(path):
    """Write a TestPlan.md with validated frontmatter and proper structure."""
    Path(path).write_text(TESTPLAN_VALID_BODY)
    write_frontmatter(str(path), {**VALID_TEST_PLAN_DATA}, "test-plan")


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
