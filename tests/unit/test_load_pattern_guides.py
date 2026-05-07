"""
Unit tests for scripts/load_pattern_guides.py

Tests loading repository instructions and pattern guides.
"""

import json

from scripts.load_pattern_guides import load_pattern_guides


def test_finds_and_loads_guides(tmp_path):
    """Should find repo instructions and pattern guides, read content."""
    (tmp_path / "CLAUDE.md").write_text("Repo context")
    rules_dir = tmp_path / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "pytest-tests.md").write_text("Pytest patterns")

    result = load_pattern_guides(str(tmp_path), "pytest")
    data = json.loads(result)

    assert "CLAUDE.md" in data['repo_instructions_files']
    assert "Repo context" in data['repo_instructions_content']
    assert ".claude/rules/pytest-tests.md" in data['pattern_guide_files'][0]
    assert "Pytest patterns" in data['pattern_guide_content']
    assert data['needs_generation'] is False


def test_detects_needs_generation_when_empty(tmp_path):
    """Should set needs_generation=true when no pattern guides found."""
    result = load_pattern_guides(str(tmp_path), "pytest")
    data = json.loads(result)

    assert data['needs_generation'] is True
    assert data['pattern_guide_files'] == []
