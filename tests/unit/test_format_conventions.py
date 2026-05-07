"""Unit tests for scripts/format_conventions.py"""

from scripts.format_conventions import format_conventions


def test_formats_conventions_as_markdown():
    """Should format conventions dict as markdown."""
    conventions = {
        'repo_name': 'opendatahub-tests',
        'framework': 'pytest',
        'test_file_pattern': 'tests/**/test_*.py',
        'test_function_pattern': 'test_*',
        'import_style': 'Absolute imports preferred',
        'markers': ['smoke', 'tier1', 'api'],
        'linting_tools': ['ruff', 'flake8', None],
        'test_directories': ['tests', 'integration']
    }

    result = format_conventions(conventions)

    assert '# Test Implementation Conventions for opendatahub-tests' in result
    assert '**pytest**' in result
    assert '`smoke`' in result
    assert '`tier1`' in result
    assert 'ruff' in result
    assert 'flake8' in result


def test_handles_minimal_conventions():
    """Should handle conventions with minimal data."""
    conventions = {
        'framework': 'pytest',
        'markers': []
    }

    result = format_conventions(conventions)

    assert '**pytest**' in result
    assert 'Pytest Markers' not in result  # No markers section if empty
