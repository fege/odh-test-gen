"""
Unit tests for scripts/detect_components.py

Tests component detection and repository mapping logic.
"""

import json
from pathlib import Path

import pytest

from scripts.detect_components import detect_components


class TestDetectComponents:
    """Test detect_components function."""

    def _create_testplan(self, tmp_path, components=None, scope_text="", endpoints_text=""):
        """Helper to create TestPlan.md with minimal valid frontmatter."""
        components_yaml = ""
        if components is not None:
            if components:
                components_yaml = "components:\n" + "\n".join(f"  - {c}" for c in components)
            else:
                components_yaml = "components: []"

        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(f"""---
source_key: RHAISTRAT-1507
feature: Test Feature
version: 1.0.0
{components_yaml}
---

## 1. Test Objectives
Test objectives here.

### 1.2 Scope
{scope_text}

## 4. Endpoints Under Test
{endpoints_text}
""")

        # Create test_cases directory
        tc_dir = tmp_path / "test_cases"
        tc_dir.mkdir()
        (tc_dir / "INDEX.md").write_text("# Test Cases Index")

        return testplan

    def test_preserves_frontmatter_casing_and_deduplicates(self, tmp_path):
        """
        Should preserve original casing AND deduplicate case-insensitively.

        When frontmatter has "Notebooks" and content has "notebooks",
        should keep only "Notebooks" (frontmatter casing preferred).
        """
        self._create_testplan(
            tmp_path,
            components=["AI Hub", "Notebooks"],
            scope_text="Tests the ODH Dashboard and notebooks features."
        )

        result = detect_components(str(tmp_path))
        data = json.loads(result)

        # Should preserve original casing from frontmatter
        assert "AI Hub" in data['frontmatter_components'], \
            f"Should preserve 'AI Hub' casing, got: {data['frontmatter_components']}"
        assert "Notebooks" in data['frontmatter_components'], \
            f"Should preserve 'Notebooks' casing, got: {data['frontmatter_components']}"

        # Should NOT have lowercase duplicates
        assert "ai hub" not in data['frontmatter_components'], \
            "Should not have lowercase 'ai hub' when 'AI Hub' exists in frontmatter"
        assert "notebooks" not in data['frontmatter_components'], \
            "Should not have lowercase 'notebooks' when 'Notebooks' exists in frontmatter"

        # Should result in: "AI Hub", "Notebooks", "dashboard" (no "notebooks" duplicate)
        lowercase_all = [c.lower() for c in data['all_components']]
        assert lowercase_all.count('notebooks') == 1, \
            f"Should have exactly 1 'notebooks' (case-insensitive), got: {data['all_components']}"

        # Check specific repo mappings
        assert data['repos']['AI Hub'] == 'opendatahub-io/model-registry'
        assert data['repos']['Notebooks'] == 'opendatahub-io/notebooks'

        # Check unique_repos includes both
        assert 'opendatahub-io/model-registry' in data['unique_repos']
        assert 'opendatahub-io/notebooks' in data['unique_repos']

    def test_detects_content_components_only(self, tmp_path):
        """Should extract components from content when no frontmatter components."""
        self._create_testplan(
            tmp_path,
            components=None,
            scope_text="Tests the ODH Dashboard REST API for managing notebooks.",
            endpoints_text="| `/api/v1/dashboard/config` | GET | Config |\n| `/api/v1/notebooks` | POST | Create |"
        )

        result = detect_components(str(tmp_path))
        data = json.loads(result)

        assert 'dashboard' in data['content_components']
        assert 'notebooks' in data['content_components']

        assert data['repos']['dashboard'] == 'opendatahub-io/odh-dashboard'
        assert data['repos']['notebooks'] == 'opendatahub-io/notebooks'

    def test_merges_and_deduplicates_components(self, tmp_path):
        """Should merge frontmatter and content components, deduplicating."""
        self._create_testplan(
            tmp_path,
            components=["KServe"],
            scope_text="Tests KServe model serving and MLServer runtime.",
            endpoints_text="| `/api/v1/serving/models` | GET | Models |"
        )

        result = detect_components(str(tmp_path))
        data = json.loads(result)

        assert 'KServe' in data['frontmatter_components']
        assert 'kserve' in data['content_components']
        assert 'mlserver' in data['content_components']

        # Should deduplicate kserve (appears in both frontmatter and content)
        # With casing preserved, all_components will have 'KServe' (from frontmatter), not 'kserve'
        lowercase_components = [c.lower() for c in data['all_components']]
        kserve_count = lowercase_components.count('kserve')
        assert kserve_count == 1, f"Should have exactly 1 kserve (case-insensitive), got: {data['all_components']}"

    def test_handles_multiple_components_to_same_repo(self, tmp_path):
        """Should handle multiple components mapping to the same repository."""
        self._create_testplan(
            tmp_path,
            components=["Notebooks", "Workbenches"]
        )

        result = detect_components(str(tmp_path))
        data = json.loads(result)

        assert data['repos']['Notebooks'] == 'opendatahub-io/notebooks'
        assert data['repos']['Workbenches'] == 'opendatahub-io/notebooks'

        # Both map to same repo, unique_repos should have 1 entry
        assert len(data['unique_repos']) == 1
        assert data['unique_repos'][0] == 'opendatahub-io/notebooks'

    def test_handles_unknown_components(self, tmp_path):
        """Should handle components not in the mapping."""
        self._create_testplan(
            tmp_path,
            components=["UnknownComponent", "Notebooks"]
        )

        result = detect_components(str(tmp_path))
        data = json.loads(result)

        # Unknown component maps to null
        assert data['repos']['UnknownComponent'] is None

        # Known component still maps correctly
        assert data['repos']['Notebooks'] == 'opendatahub-io/notebooks'

        # unique_repos should only include valid repos (not null)
        assert 'opendatahub-io/notebooks' in data['unique_repos']
        assert None not in data['unique_repos']

    def test_prioritizes_frontmatter_components(self, tmp_path):
        """Should mark frontmatter components separately for priority."""
        self._create_testplan(
            tmp_path,
            components=["AI Hub"],
            scope_text="Tests dashboard and notebooks."
        )

        result = detect_components(str(tmp_path))
        data = json.loads(result)

        assert len(data['frontmatter_components']) == 1
        assert 'AI Hub' in data['frontmatter_components']

        # content should have dashboard, notebooks
        assert 'dashboard' in data['content_components']
        assert 'notebooks' in data['content_components']

        # repos_from_frontmatter should only include AI Hub's repo
        assert 'opendatahub-io/model-registry' in data['repos_from_frontmatter']
        assert 'opendatahub-io/odh-dashboard' not in data['repos_from_frontmatter']

    def test_handles_missing_testplan(self, tmp_path):
        """Should raise error if TestPlan.md is missing."""
        with pytest.raises(FileNotFoundError, match="TestPlan.md not found"):
            detect_components(str(tmp_path))

    def test_handles_missing_or_empty_components(self, tmp_path):
        """Should handle missing or empty components field."""
        # Test with empty list
        self._create_testplan(
            tmp_path,
            components=[],
            scope_text="Tests dashboard API."
        )

        result = detect_components(str(tmp_path))
        data = json.loads(result)

        assert data['frontmatter_components'] == []
        assert 'dashboard' in data['content_components']

    def test_case_insensitive_matching(self, tmp_path):
        """Should preserve casing but lookup repos case-insensitively."""
        self._create_testplan(
            tmp_path,
            components=["AI Hub", "Model Registry"]
        )

        result = detect_components(str(tmp_path))
        data = json.loads(result)

        # Should preserve original casing
        assert 'AI Hub' in data['frontmatter_components']
        assert 'Model Registry' in data['frontmatter_components']

        # Both map to same repo (lookup is case-insensitive)
        assert data['repos']['AI Hub'] == 'opendatahub-io/model-registry'
        assert data['repos']['Model Registry'] == 'opendatahub-io/model-registry'

        assert len(data['unique_repos']) == 1
