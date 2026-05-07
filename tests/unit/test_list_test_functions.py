"""
Unit tests for scripts/list_test_functions.py

Tests extraction of test function definitions from Python test files.
"""

import json

import pytest

from scripts.list_test_functions import list_test_functions


def test_extracts_test_functions_with_docstrings(tmp_path):
    """Should extract function names, line numbers, and docstrings."""
    test_file = tmp_path / "test_example.py"
    test_file.write_text('''
def test_create_notebook():
    """Test notebook creation via API."""
    assert True

def helper_function():
    """Not a test."""
    return 42

def test_delete_notebook():
    assert False
''')

    result = list_test_functions(str(test_file))
    data = json.loads(result)

    assert len(data['functions']) == 2
    assert data['functions'][0]['name'] == 'test_create_notebook'
    assert data['functions'][0]['line'] == 2
    assert data['functions'][0]['docstring'] == 'Test notebook creation via API.'
    assert data['functions'][1]['name'] == 'test_delete_notebook'
    assert data['functions'][1]['docstring'] is None


def test_handles_missing_file(tmp_path):
    """Should raise error if file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        list_test_functions(str(tmp_path / "nonexistent.py"))
