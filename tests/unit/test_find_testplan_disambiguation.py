"""Test that _find_testplan_in_repo disambiguates multiple TestPlan.md files."""

import tempfile
from pathlib import Path
from scripts.repo import _find_testplan_in_repo


def test_find_testplan_with_multiple_features_uses_branch_hint():
    """
    Verify _find_testplan_in_repo uses branch hint to pick correct feature.

    Scenario: Repo has multiple features (e.g., opendatahub-test-plans).
    When branch is "test-plan/RHAISTRAT-1507", should pick the feature
    with matching source_key in TestPlan.md frontmatter.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create feature 1: evalhub_metrics (RHAISTRAT-1507)
        feature1 = repo_path / "evalhub_metrics"
        feature1.mkdir()
        (feature1 / "TestPlan.md").write_text("""---
feature: evalhub_metrics
source_key: RHAISTRAT-1507
---
# Test Plan 1
""")

        # Create feature 2: evalhub_metrics_discovery (RHAISTRAT-1525)
        feature2 = repo_path / "evalhub_metrics_discovery"
        feature2.mkdir()
        (feature2 / "TestPlan.md").write_text("""---
feature: evalhub_metrics_discovery
source_key: RHAISTRAT-1525
---
# Test Plan 2
""")

        # Call with branch hint matching feature 1
        result = _find_testplan_in_repo(str(repo_path), branch_hint="test-plan/RHAISTRAT-1507")

        assert result == str(feature1), \
            f"Should find evalhub_metrics, got {result}"


def test_find_testplan_with_single_feature_ignores_branch_hint():
    """Verify single TestPlan.md is found regardless of branch hint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create single feature
        feature = repo_path / "my_feature"
        feature.mkdir()
        (feature / "TestPlan.md").write_text("# Test Plan")

        # Branch hint doesn't matter when only one exists
        result = _find_testplan_in_repo(str(repo_path), branch_hint="wrong-branch")

        assert result == str(feature)


def test_find_testplan_with_multiple_features_no_hint_returns_none():
    """Verify multiple TestPlan.md without branch hint returns None (ambiguous)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create two features
        (repo_path / "feature1").mkdir()
        (repo_path / "feature1" / "TestPlan.md").write_text("# Test Plan 1")
        (repo_path / "feature2").mkdir()
        (repo_path / "feature2" / "TestPlan.md").write_text("# Test Plan 2")

        # No branch hint = ambiguous
        result = _find_testplan_in_repo(str(repo_path))

        assert result is None, "Should return None when ambiguous"


def test_find_testplan_with_no_testplan_returns_none():
    """Verify empty repo returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _find_testplan_in_repo(tmpdir)
        assert result is None
