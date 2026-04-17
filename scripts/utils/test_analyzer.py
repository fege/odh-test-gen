#!/usr/bin/env python3
"""
Test analysis utilities.

Analyzes parsed TC data to identify patterns for test generation.
Framework-agnostic - identifies what's common without prescribing implementation.
"""

from typing import Dict, List


def identify_common_setup_requirements(test_cases: List[Dict]) -> List[Dict]:
    """
    Identify preconditions used by multiple test cases.

    Framework-agnostic - finds common setup requirements without prescribing
    how to implement them.

    Args:
        test_cases: List of parsed TC dicts (must have 'test_case_id', preconditions optional)

    Returns:
        List of common requirements, sorted by usage count (descending):
        [{
            'requirement': 'RHOAI cluster deployed',
            'used_by_tcs': ['TC-API-001', 'TC-API-002', 'TC-E2E-001'],
            'count': 3,
            'tc_priorities': ['P0', 'P1', 'P0']
        }]

        Only includes requirements used by 2+ test cases.
        Returns empty list if no common requirements found.

    Raises:
        ValueError: If any TC is missing test_case_id
    """
    # Count occurrences of each precondition
    precondition_usage = {}

    for tc in test_cases:
        # Validate required field
        if 'test_case_id' not in tc or not tc['test_case_id']:
            raise ValueError(f"TC missing required field 'test_case_id': {tc}")

        tc_id = tc['test_case_id']
        tc_priority = tc.get('priority', 'P2')

        preconditions = tc.get('preconditions', [])
        if not preconditions:
            continue  # Skip TCs with no preconditions

        for precond in preconditions:
            # Normalize (strip whitespace, lowercase for matching)
            normalized = precond.strip().lower()

            if not normalized:
                continue  # Skip empty strings

            if normalized not in precondition_usage:
                precondition_usage[normalized] = {
                    'original': precond.strip(),  # Keep original case
                    'used_by_tcs': [],
                    'tc_priorities': [],
                }

            precondition_usage[normalized]['used_by_tcs'].append(tc_id)
            precondition_usage[normalized]['tc_priorities'].append(tc_priority)

    # Filter to only those used by 2+ TCs
    common_requirements = []
    for normalized, data in precondition_usage.items():
        if len(data['used_by_tcs']) >= 2:
            common_requirements.append({
                'requirement': data['original'],
                'used_by_tcs': data['used_by_tcs'],
                'count': len(data['used_by_tcs']),
                'tc_priorities': data['tc_priorities'],
            })

    # Sort by count (descending) - most common first
    common_requirements.sort(key=lambda x: x['count'], reverse=True)

    return common_requirements
