"""Unit tests for scripts/format_file_result.py"""

import json

from scripts.format_file_result import format_file_result


def test_formats_result_with_content(tmp_path):
    """Should read file content and format as JSON."""
    test_file = tmp_path / "test_file_0.py"
    test_file.write_text("""import pytest

def test_example():
    assert True
""")

    # Temporarily override the path
    import scripts.format_file_result
    original_path = scripts.format_file_result.Path
    scripts.format_file_result.Path = lambda p: tmp_path / p.replace("/tmp/", "")

    try:
        metadata = {
            "file_index": 0,
            "file_path": "tests/test_api.py",
            "tc_ids": ["TC-API-001"],
            "functions": [{"tc_id": "TC-API-001", "name": "test_create", "score": 9, "verdict": "Ready"}],
            "quality_summary": {"ready_count": 1, "good_count": 0, "avg_score": 9.0}
        }

        result = format_file_result(metadata)
        data = json.loads(result)

        assert data["file_path"] == "tests/test_api.py"
        assert "import pytest" in data["content"]
        assert "def test_example():" in data["content"]
        assert data["test_cases"] == ["TC-API-001"]
        assert len(data["functions"]) == 1
        assert data["draft_files"] == []
        assert data["errors"] == []
    finally:
        scripts.format_file_result.Path = original_path


def test_includes_draft_files_and_errors(tmp_path):
    """Should include draft_files and errors if provided."""
    test_file = tmp_path / "test_file_0.py"
    test_file.write_text("def test_example(): pass")

    import scripts.format_file_result
    original_path = scripts.format_file_result.Path
    scripts.format_file_result.Path = lambda p: tmp_path / p.replace("/tmp/", "")

    try:
        metadata = {
            "file_index": 0,
            "file_path": "tests/test_api.py",
            "tc_ids": ["TC-API-001", "TC-API-002"],
            "functions": [{"tc_id": "TC-API-001", "name": "test_create", "score": 8, "verdict": "Good"}],
            "quality_summary": {"ready_count": 0, "good_count": 1, "flagged_count": 1, "avg_score": 5.0},
            "draft_files": [{"tc_id": "TC-API-002", "reason": "Score 2/10", "score": 2}],
            "errors": []
        }

        result = format_file_result(metadata)
        data = json.loads(result)

        assert len(data["functions"]) == 1
        assert len(data["draft_files"]) == 1
        assert data["draft_files"][0]["tc_id"] == "TC-API-002"
    finally:
        scripts.format_file_result.Path = original_path
