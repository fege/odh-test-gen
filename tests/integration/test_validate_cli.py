"""Smoke tests for scripts/validate.py CLI wiring."""

import sys

import pytest

from scripts import validate
from scripts.utils.frontmatter_utils import write_frontmatter
from tests.constants import VALID_TEST_GAPS_DATA


@pytest.mark.parametrize("subcommand", ["feature-dir", "test-cases", "all"])
def test_subcommand_parses_and_exits_0(feature_dir, subcommand):
    sys.argv = ["validate.py", subcommand, feature_dir]
    with pytest.raises(SystemExit) as exc_info:
        validate.main()
    assert exc_info.value.code == 0


def test_gap_counts_parses_and_exits_0(tmp_path):
    data = {**VALID_TEST_GAPS_DATA, "gap_count": 10}
    write_frontmatter(str(tmp_path / "TestPlanGaps.md"), data, "test-gaps")

    sys.argv = ["validate.py", "gap-counts", str(tmp_path), "3", "9", "2"]
    with pytest.raises(SystemExit) as exc_info:
        validate.main()
    assert exc_info.value.code == 0
