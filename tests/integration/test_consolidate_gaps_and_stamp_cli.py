"""
Integration tests for scripts/consolidate_gaps_and_stamp.py CLI.

This script wraps consolidate_gaps() + write_frontmatter_with_body() into the single
call test-plan-create's Step 3.5 needs: consolidate raw analyzer gap output, write
TestPlanGaps.md (body + stamped frontmatter) in one shot, delete the staged temp
source files, and print {"gap_count": int, "status": str, "next": str} to stdout.

Pure gap-consolidation logic (dedup, grouping, status derivation) is already covered by
tests/unit/test_consolidate_gaps.py — this file covers frontmatter stamping, temp-file
cleanup, the gaps-menu next-action gate, and failing before any output is written.
"""

import json
import os
import subprocess

import pytest

from scripts.utils.frontmatter_utils import read_frontmatter
from tests.constants import REPO_ROOT
from tests.consts.gaps_constants import (
    GAPS_ENDPOINTS_DUPLICATE,
    GAPS_INFRA_SINGLETON,
    GAPS_NEXT_PROCEED,
    GAPS_NEXT_PROMPT_USER,
    GAPS_RISKS_DUPLICATE,
)

LAST_UPDATED = "1999-12-31"


def _run_cli(*extra_args, env_overrides=None):
    env = os.environ.copy()
    env.pop("CI", None)
    env.pop("CLAUDE_NON_INTERACTIVE", None)
    if env_overrides:
        env.update(env_overrides)
    cmd = [
        "uv",
        "run",
        "python",
        str(REPO_ROOT / "scripts" / "consolidate_gaps_and_stamp.py"),
        "--last-updated",
        LAST_UPDATED,
        *extra_args,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=REPO_ROOT, env=env)


@pytest.fixture
def feature_dir(tmp_path):
    d = tmp_path / "TestFeature"
    d.mkdir(parents=True, exist_ok=True)
    return d


class TestConsolidateGapsAndStampCLI:
    @pytest.mark.parametrize(
        "sources,expected_gap_count,expected_status,body_contains,body_excludes",
        [
            (
                {
                    "endpoints": GAPS_ENDPOINTS_DUPLICATE,
                    "risks": GAPS_RISKS_DUPLICATE,
                    "infra": GAPS_INFRA_SINGLETON,
                },
                3,
                "Open",
                "# Gaps — Test Feature",
                None,
            ),
            (
                {"endpoints": "## Gaps\n\nNo gaps identified.\n"},
                0,
                "Resolved",
                "No gaps identified.",
                "# Gaps — Test Feature\n\n-",
            ),
        ],
        ids=["gaps-present", "no-gaps"],
    )
    def test_writes_gaps_file_stamps_frontmatter_and_cleans_temp_files(
        self, feature_dir, sources, expected_gap_count, expected_status, body_contains, body_excludes
    ):
        source_files = {}
        for name, content in sources.items():
            path = feature_dir / f".analysis-{name}.md"
            path.write_text(content)
            source_files[name] = path
        out_file = feature_dir / "TestPlanGaps.md"

        source_args = []
        for name, path in source_files.items():
            source_args += ["--source", f"{name}={path}"]

        result = _run_cli(
            "--feature-name",
            "Test Feature",
            "--source-key",
            "RHAISTRAT-400",
            *source_args,
            "--out",
            str(out_file),
        )

        assert result.returncode == 0, result.stderr
        stdout_data = json.loads(result.stdout)
        expected_next = GAPS_NEXT_PROMPT_USER if expected_gap_count > 0 else GAPS_NEXT_PROCEED
        assert stdout_data == {
            "gap_count": expected_gap_count,
            "status": expected_status,
            "next": expected_next,
        }

        frontmatter, body = read_frontmatter(out_file)
        assert frontmatter["feature"] == "Test Feature"
        assert frontmatter["source_key"] == "RHAISTRAT-400"
        assert frontmatter["status"] == expected_status
        assert frontmatter["gap_count"] == expected_gap_count
        assert frontmatter["last_updated"] == LAST_UPDATED
        assert body_contains in body
        if body_excludes:
            assert body_excludes not in body

        for path in source_files.values():
            assert not path.exists()

    def test_missing_source_file_exits_nonzero_before_writing_output(self, feature_dir):
        out_file = feature_dir / "TestPlanGaps.md"
        nonexistent = feature_dir / ".analysis-endpoints.md"

        result = _run_cli(
            "--feature-name",
            "Test Feature",
            "--source-key",
            "RHAISTRAT-400",
            "--source",
            f"endpoints={nonexistent}",
            "--out",
            str(out_file),
        )

        assert result.returncode != 0
        stdout_data = json.loads(result.stdout)
        assert stdout_data == {"status": "failed", "error": "source_file_not_found"}
        assert not out_file.exists()

    def test_cleanup_preserves_testplan_gaps_when_source_is_out_path(self, feature_dir):
        out_file = feature_dir / "TestPlanGaps.md"
        out_file.write_text(GAPS_ENDPOINTS_DUPLICATE)

        result = _run_cli(
            "--feature-name",
            "Test Feature",
            "--source-key",
            "RHAISTRAT-400",
            "--source",
            f"endpoints={out_file}",
            "--out",
            str(out_file),
        )

        assert result.returncode == 0, result.stderr
        assert out_file.exists()
        assert "gap_count" in json.loads(result.stdout)

    def test_cleanup_skips_unverified_source_outside_feature_dir(self, feature_dir):
        outsider = feature_dir.parent / "outside-source.md"
        outsider.write_text(GAPS_ENDPOINTS_DUPLICATE)
        out_file = feature_dir / "TestPlanGaps.md"

        result = _run_cli(
            "--feature-name",
            "Test Feature",
            "--source-key",
            "RHAISTRAT-400",
            "--source",
            f"endpoints={outsider}",
            "--out",
            str(out_file),
        )

        assert result.returncode == 0, result.stderr
        assert outsider.exists()
        assert out_file.exists()

    @pytest.mark.parametrize(
        "env_overrides",
        [{"CI": "true"}, {"CLAUDE_NON_INTERACTIVE": "true"}],
        ids=["ci", "claude-non-interactive"],
    )
    def test_gaps_present_non_interactive_next_is_proceed(self, feature_dir, env_overrides):
        staging = feature_dir / ".analysis-endpoints.md"
        staging.write_text(GAPS_ENDPOINTS_DUPLICATE)
        out_file = feature_dir / "TestPlanGaps.md"

        result = _run_cli(
            "--feature-name",
            "Test Feature",
            "--source-key",
            "RHAISTRAT-400",
            "--source",
            f"endpoints={staging}",
            "--out",
            str(out_file),
            env_overrides=env_overrides,
        )

        assert result.returncode == 0, result.stderr
        stdout_data = json.loads(result.stdout)
        assert stdout_data["gap_count"] > 0
        assert stdout_data["next"] == GAPS_NEXT_PROCEED
