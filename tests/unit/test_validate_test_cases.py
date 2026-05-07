"""Unit tests for scripts/validate_test_cases.py"""

from scripts.validate_test_cases import validate_test_cases
from tests.constants import VALID_TEST_CASE_DATA


def test_invalid_file_returns_1(tmp_path):
    """Should return 1 if any file is invalid."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    (tc_dir / "TC-API-001.md").write_text("""---
test_case_id: TC-API-001
---
""")

    assert validate_test_cases(str(tmp_path), "test-case") == 1


def test_valid_file_returns_0(tmp_path):
    """Should return 0 if all files are valid."""
    tc_dir = tmp_path / "test_cases"
    tc_dir.mkdir()

    (tc_dir / "TC-API-001.md").write_text(f"""---
test_case_id: {VALID_TEST_CASE_DATA['test_case_id']}
source_key: {VALID_TEST_CASE_DATA['source_key']}
priority: {VALID_TEST_CASE_DATA['priority']}
status: {VALID_TEST_CASE_DATA['status']}
last_updated: "{VALID_TEST_CASE_DATA['last_updated']}"
automation_status: Not Started
---
## Steps
1. Step
""")

    assert validate_test_cases(str(tmp_path), "test-case") == 0


def test_no_directory_returns_0(tmp_path):
    """Should return 0 if test_cases directory doesn't exist."""
    assert validate_test_cases(str(tmp_path), "test-case") == 0
