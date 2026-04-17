"""
Unit tests for scripts/utils/test_analyzer.py

Tests identify_common_setup_requirements function.
"""

import pytest

from scripts.utils.test_analyzer import identify_common_setup_requirements


class TestIdentifyCommonSetupRequirements:
    """Test identify_common_setup_requirements function."""

    def test_finds_common_preconditions(self):
        """Should find preconditions used by 2+ TCs with case-insensitive matching."""
        test_cases = [
            {
                'test_case_id': 'TC-API-001',
                'priority': 'P0',
                'preconditions': ['  RHOAI cluster deployed  ', 'API available']
            },
            {
                'test_case_id': 'TC-API-002',
                'priority': 'P1',
                'preconditions': ['rhoai cluster deployed', 'Test data loaded']
            },
            {
                'test_case_id': 'TC-E2E-001',
                'priority': 'P0',
                'preconditions': ['RHOAI Cluster Deployed']
            },
            {
                'test_case_id': 'TC-E2E-002',  # No preconditions (optional)
            },
        ]

        result = identify_common_setup_requirements(test_cases)

        # 'RHOAI cluster deployed' appears 3 times (normalized)
        assert len(result) == 1
        assert result[0]['requirement'] == 'RHOAI cluster deployed'
        assert result[0]['count'] == 3
        assert set(result[0]['used_by_tcs']) == {'TC-API-001', 'TC-API-002', 'TC-E2E-001'}
        assert result[0]['tc_priorities'] == ['P0', 'P1', 'P0']

    def test_returns_empty_for_unique_preconditions(self):
        """Should return empty list if all preconditions are unique."""
        test_cases = [
            {'test_case_id': 'TC-001', 'preconditions': ['Unique A']},
            {'test_case_id': 'TC-002', 'preconditions': ['Unique B']},
            {'test_case_id': 'TC-003'},  # No preconditions
        ]

        result = identify_common_setup_requirements(test_cases)

        assert result == []

    def test_validates_test_case_id_required(self):
        """Should raise ValueError if test_case_id is missing."""
        test_cases = [
            {'preconditions': ['Req']},
        ]

        with pytest.raises(ValueError, match="missing required field 'test_case_id'"):
            identify_common_setup_requirements(test_cases)
