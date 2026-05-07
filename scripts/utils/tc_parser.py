#!/usr/bin/env python3
"""
Test Case (TC-*.md) file parser.

Parses TC files into structured data for test implementation.
Extracts mandatory sections reliably using regex patterns.
"""

import re
from typing import Dict, List


def parse_tc_file(tc_file_path: str, read_frontmatter_func) -> Dict:
    """
    Parse a test case file (TC-*.md) into structured data.

    Mandatory extracted fields:
    - objective: str (one-sentence test goal)
    - preconditions: list[str] (setup requirements)
    - test_steps: list[str] (numbered action steps)
    - expected_results: list[str] (expected outcomes)

    Optional (kept in body):
    - Test Data, Expected Response, Validation, Notes (raw markdown)

    Args:
        tc_file_path: Path to TC-*.md file
        read_frontmatter_func: Function to read frontmatter (returns tuple of (dict, str))

    Returns:
        dict with:
            - All frontmatter fields (test_case_id, priority, category, source_key, etc.)
            - objective: str
            - preconditions: list[str]
            - test_steps: list[str]
            - expected_results: list[str]
            - body: str (unparsed remainder with optional sections)

    Raises:
        ValueError: If mandatory sections are missing or empty
    """
    # Read frontmatter and body
    frontmatter, full_body = read_frontmatter_func(tc_file_path)

    # Extract sections
    sections = _parse_sections(full_body)

    # Extract mandatory: Objective
    objective = _extract_objective_text(sections.get('Objective', ''))
    if not objective:
        raise ValueError(f"{tc_file_path}: Missing or empty **Objective**")

    # Extract mandatory: Preconditions (bullet list)
    preconditions = _extract_bullet_list(sections.get('Preconditions', ''))
    if not preconditions:
        raise ValueError(f"{tc_file_path}: Missing or empty **Preconditions**")

    # Extract mandatory: Test Steps (numbered list)
    test_steps = _extract_numbered_list(sections.get('Test Steps', ''))
    if not test_steps:
        raise ValueError(f"{tc_file_path}: Missing or empty **Test Steps**")

    # Extract mandatory: Expected Results (bullet list)
    expected_results = _extract_bullet_list(sections.get('Expected Results', ''))
    if not expected_results:
        raise ValueError(f"{tc_file_path}: Missing or empty **Expected Results**")

    # Build body with only optional sections (not parsed, kept as-is)
    optional_sections = ['Test Data', 'Expected Response', 'Validation', 'Notes']
    body_parts = []
    for section_name in optional_sections:
        if section_name in sections and sections[section_name].strip():
            # Keep section header + content as-is
            body_parts.append(f"**{section_name}**:\n{sections[section_name]}")

    body = '\n\n'.join(body_parts)

    # Build result
    return {
        # All frontmatter fields
        **frontmatter,

        # Mandatory extracted sections
        'objective': objective,
        'preconditions': preconditions,
        'test_steps': test_steps,
        'expected_results': expected_results,

        # Unparsed remainder (optional sections only)
        'body': body,
    }


def _parse_sections(body: str) -> Dict[str, str]:
    """
    Parse TC body into sections by **SectionName**: pattern.

    Handles:
    - **Objective**: {text}
    - **Preconditions**:
    - **Test Steps**:
    - **Expected Results**:
    - **Test Data**:
    - **Expected Response**:
    - **Validation**:
    - **Notes**:

    Returns:
        dict mapping section name to section content (without header)
    """
    sections = {}

    # Pattern: **SectionName**: (allows spaces in name)
    # Matches: **Objective**:, **Test Steps**:, **Expected Results**:
    section_pattern = r'\*\*([A-Z][A-Za-z ]+)\*\*:\s*'

    # Find all section headers with their positions
    matches = list(re.finditer(section_pattern, body))

    if not matches:
        # No sections found - maybe malformed file
        return {}

    for i, match in enumerate(matches):
        section_name = match.group(1).strip()
        content_start = match.end()

        # Content ends at next section or end of body
        if i + 1 < len(matches):
            content_end = matches[i + 1].start()
        else:
            content_end = len(body)

        content = body[content_start:content_end].strip()
        sections[section_name] = content

    return sections


def _extract_objective_text(objective_content: str) -> str:
    """
    Extract objective text.

    Objective format: **Objective**: {one sentence}

    Args:
        objective_content: Content after **Objective**: header

    Returns:
        Objective text (trimmed) or empty string
    """
    return objective_content.strip()


def _extract_bullet_list(section_content: str) -> List[str]:
    """
    Extract items from markdown bullet list.

    Handles:
    - Lines starting with '- ' or '* '
    - Multi-line items (continuation lines without bullets)
    - Empty lines between items

    Args:
        section_content: Section text containing bullet list

    Returns:
        List of items (without bullet markers, multi-line items joined)
    """
    if not section_content.strip():
        return []

    items = []
    current_item = None

    for line in section_content.split('\n'):
        stripped = line.strip()

        # Empty line - end current item
        if not stripped:
            if current_item:
                items.append(current_item.strip())
                current_item = None
            continue

        # New bullet item
        if stripped.startswith('- ') or stripped.startswith('* '):
            # Save previous item
            if current_item:
                items.append(current_item.strip())
            # Start new item (remove bullet marker)
            current_item = stripped[2:]

        # Continuation line (no bullet, part of current item)
        elif current_item is not None:
            current_item += ' ' + stripped

        # Text before first bullet (ignore - shouldn't happen in well-formed TC)
        else:
            pass

    # Save last item
    if current_item:
        items.append(current_item.strip())

    return items


def _extract_numbered_list(section_content: str) -> List[str]:
    """
    Extract items from markdown numbered list.

    Handles:
    - Lines starting with '1. ', '2. ', etc.
    - Multi-line items (continuation lines without numbers)
    - Empty lines between items
    - Non-sequential numbers (e.g., 1, 2, 5 - just treats as list)

    Args:
        section_content: Section text containing numbered list

    Returns:
        List of items (without numbers, multi-line items joined)
    """
    if not section_content.strip():
        return []

    items = []
    current_item = None

    for line in section_content.split('\n'):
        stripped = line.strip()

        # Empty line - end current item
        if not stripped:
            if current_item:
                items.append(current_item.strip())
                current_item = None
            continue

        # New numbered item (matches: '1. ', '2. ', '10. ', etc.)
        if re.match(r'^\d+\.\s+', stripped):
            # Save previous item
            if current_item:
                items.append(current_item.strip())
            # Start new item (remove number prefix)
            current_item = re.sub(r'^\d+\.\s+', '', stripped)

        # Continuation line (no number, part of current item)
        elif current_item is not None:
            current_item += ' ' + stripped

        # Text before first number (ignore - shouldn't happen)
        else:
            pass

    # Save last item
    if current_item:
        items.append(current_item.strip())

    return items


def extract_category_from_tc_id(tc_id: str) -> str:
    """
    Extract category from TC ID.

    Args:
        tc_id: Test case ID (e.g., 'TC-API-001', 'TC-E2E-042')

    Returns:
        Category name in lowercase (e.g., 'api', 'e2e')
        Returns 'other' if format is invalid

    Examples:
        >>> extract_category_from_tc_id("TC-API-001")
        'api'
        >>> extract_category_from_tc_id("TC-E2E-042")
        'e2e'
        >>> extract_category_from_tc_id("INVALID")
        'other'
    """
    parts = tc_id.split('-')
    return parts[1].lower() if len(parts) >= 2 and parts[1] else 'other'


def extract_title_from_tc_file(tc_file: str) -> str:
    """
    Extract title from TC markdown file.

    Tries multiple sources in order of preference:
    1. Frontmatter 'title' field
    2. ## Title section in body
    3. Frontmatter 'test_case_id' as fallback

    Args:
        tc_file: Path to TC-*.md file

    Returns:
        Title string

    Examples:
        Frontmatter with title:
        ---
        title: Create notebook
        ---
        → Returns: "Create notebook"

        Body with ## Title:
        ## Title
        Delete notebook
        → Returns: "Delete notebook"
    """
    from .frontmatter_utils import read_frontmatter

    frontmatter, body = read_frontmatter(tc_file)

    # Try frontmatter title first
    if 'title' in frontmatter:
        return frontmatter['title']

    # Try to find first ## Title section in body
    title_match = re.search(
        r'^##\s+Title\s*\n(.+?)(?:\n##|\Z)',
        body,
        re.MULTILINE | re.DOTALL
    )
    if title_match:
        return title_match.group(1).strip()

    # Fallback: use TC ID
    return frontmatter.get('test_case_id', 'test')
