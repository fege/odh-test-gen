#!/usr/bin/env python3
"""
Repository discovery helpers.

Extracts repository indicators from TestPlan.md and TC files to identify
which GitHub repository is being tested (for test-plan.case-implement).

Non-interactive utilities - all user interaction handled by calling skill.
"""

import re
from typing import Dict, List

from .component_map import COMPONENT_REPO_MAP
from .frontmatter_utils import read_frontmatter
from .tc_parser import parse_tc_file


def extract_repo_indicators(
    testplan_path: str,
    tc_files: List[str]
) -> Dict[str, List[str]]:
    """
    Extract repository indicators from TestPlan.md and TC files.

    Used for repository discovery (Step 0.4 in test-plan.case-implement).

    Extracts:
    1. Endpoints from TestPlan.md Section 4
    2. Components from TestPlan.md Section 1.2 (Scope)
    3. Components from TC preconditions (samples up to 3 TC files)

    Uses hardcoded component keywords for common opendatahub-io repos.

    Args:
        testplan_path: Path to TestPlan.md
        tc_files: List of paths to TC-*.md files (will sample up to 3)

    Returns:
        dict with:
            - components: list[str] (component names, lowercased, deduplicated)
            - endpoints: list[str] (API paths like /api/v1/notebooks)
    """
    # Load component keywords from authoritative map
    component_keywords = list(COMPONENT_REPO_MAP.keys())

    # Read TestPlan.md
    with open(testplan_path, 'r', encoding='utf-8') as f:
        testplan_content = f.read()

    components = []
    endpoints = []

    # --- Extract from Section 1.2 (Scope) ---
    scope_match = re.search(
        r'###?\s+1\.2[:\s]+Scope(.*?)(?=###|\Z)',
        testplan_content,
        re.DOTALL | re.IGNORECASE
    )
    if scope_match:
        scope_text = scope_match.group(1)

        # Extract component keywords
        for keyword in component_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', scope_text, re.IGNORECASE):
                components.append(keyword)

    # --- Extract from Section 4 (Endpoints/Methods Under Test) ---
    section4_match = re.search(
        r'###?\s+4[:\s]+.*?(?:Endpoints?|Methods?)(.*?)(?=###|\Z)',
        testplan_content,
        re.DOTALL | re.IGNORECASE
    )
    if section4_match:
        endpoints_text = section4_match.group(1)

        # Extract API paths (e.g., /api/v1/notebooks, /api/service-mesh/config)
        api_pattern = r'(/api/[^\s\)\|]+)'
        api_endpoints = re.findall(api_pattern, endpoints_text)
        endpoints.extend(api_endpoints)

        # Extract component hints from endpoint paths
        # e.g., /api/v1/notebooks → "notebooks"
        for endpoint in api_endpoints:
            parts = endpoint.split('/')
            for part in parts:
                if part and part not in ['api', 'v1', 'v2', 'v3']:
                    components.append(part)

    # --- Sample up to 3 TC files for component mentions ---
    sample_tc_files = tc_files[:3]
    for tc_file in sample_tc_files:
        try:
            tc_data = parse_tc_file(tc_file, read_frontmatter)

            # Look for component mentions in preconditions
            for precond in tc_data.get('preconditions', []):
                for keyword in component_keywords:
                    if re.search(r'\b' + re.escape(keyword) + r'\b', precond, re.IGNORECASE):
                        components.append(keyword)
        except (FileNotFoundError, ValueError, TypeError, ImportError):
            # Skip if TC file is malformed, missing, or parse error
            continue

    # Deduplicate and clean
    components = list(set([c.lower().strip() for c in components if c]))
    endpoints = list(set([e.strip() for e in endpoints if e]))

    return {
        'components': components,
        'endpoints': endpoints,
    }

