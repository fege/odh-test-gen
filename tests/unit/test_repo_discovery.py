"""
Unit tests for scripts/utils/repo_discovery.py

Tests extract_repo_indicators logic with hardcoded component keywords.
"""

from scripts.utils.repo_discovery import extract_repo_indicators
from tests.integration.constants import (
    TESTPLAN_WITH_ENDPOINTS,
    TESTPLAN_WITH_SCOPE_COMPONENTS,
    TESTPLAN_FOR_TC_PRECONDITIONS,
    TC_WITH_COMPONENT_MENTIONS,
    TESTPLAN_WITH_DUPLICATES,
)


class TestExtractRepoIndicators:
    """Test extract_repo_indicators extraction logic."""

    def test_extract_endpoints_from_section_4(self, tmp_path):
        """Should extract API endpoints from Section 4."""
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_WITH_ENDPOINTS)

        result = extract_repo_indicators(str(testplan), [])

        assert '/api/v1/notebooks' in result['endpoints']
        assert '/api/v1/models' in result['endpoints']
        assert 'notebooks' in result['components']

    def test_extract_components_from_scope(self, tmp_path):
        """Should extract components from Section 1.2 Scope."""
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_WITH_SCOPE_COMPONENTS)

        result = extract_repo_indicators(str(testplan), [])

        assert 'dashboard' in result['components']
        assert 'model-registry' in result['components']

    def test_extract_from_tc_preconditions(self, tmp_path):
        """Should extract components from TC preconditions."""
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_FOR_TC_PRECONDITIONS)

        tc_file = tmp_path / "TC-API-001.md"
        tc_file.write_text(TC_WITH_COMPONENT_MENTIONS)

        result = extract_repo_indicators(str(testplan), [str(tc_file)])

        assert 'notebooks' in result['components']
        assert 'model-registry' in result['components']

    def test_deduplicates_components(self, tmp_path):
        """Should deduplicate component mentions."""
        testplan = tmp_path / "TestPlan.md"
        testplan.write_text(TESTPLAN_WITH_DUPLICATES)

        result = extract_repo_indicators(str(testplan), [])

        assert result['components'].count('notebooks') == 1
        assert result['components'].count('dashboard') == 1

