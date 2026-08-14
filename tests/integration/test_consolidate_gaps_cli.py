"""
Integration tests for scripts/consolidate_gaps.py CLI.

Tests subprocess invocation with temp .gaps-*.md files → TestPlanGaps.md body + JSON stdout.
Consolidation logic is covered by unit tests; these test the CLI contract only.
"""

import json
import subprocess

import pytest

from tests.constants import REPO_ROOT
from tests.consts.gaps_constants import GAPS_ENDPOINTS_DUPLICATE, GAPS_INFRA_SINGLETON, GAPS_RISKS_DUPLICATE


@pytest.fixture
def feature_dir(tmp_path):
    """Create a temporary feature directory for gap files."""
    return tmp_path / "TestFeature"


@pytest.fixture
def gap_files(feature_dir):
    """Create temporary .gaps-*.md files."""
    feature_dir.mkdir(parents=True, exist_ok=True)

    endpoints_file = feature_dir / ".gaps-endpoints.md"
    risks_file = feature_dir / ".gaps-risks.md"
    infra_file = feature_dir / ".gaps-infra.md"

    endpoints_file.write_text(GAPS_ENDPOINTS_DUPLICATE)
    risks_file.write_text(GAPS_RISKS_DUPLICATE)
    infra_file.write_text(GAPS_INFRA_SINGLETON)

    return {
        "endpoints": endpoints_file,
        "risks": risks_file,
        "infra": infra_file,
    }


class TestConsolidateGapsCLI:
    """CLI contract tests: subprocess invocation, file I/O, JSON stdout."""

    def test_cli_writes_body_and_outputs_valid_json(self, gap_files, feature_dir):
        """End-to-end: CLI reads temp gap files, writes TestPlanGaps.md, prints valid JSON to stdout."""
        output_file = feature_dir / "TestPlanGaps.md"

        cmd = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "consolidate_gaps.py"),
            "--feature-name",
            "Test Feature",
            "--source",
            f"endpoints={gap_files['endpoints']}",
            "--source",
            f"risks={gap_files['risks']}",
            "--source",
            f"infra={gap_files['infra']}",
            "--out",
            str(output_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=REPO_ROOT)

        stdout_data = json.loads(result.stdout)
        assert 3 == stdout_data["gap_count"]
        assert stdout_data["status"] == "Open"

        # Body file written
        assert output_file.exists()
        body_content = output_file.read_text()
        assert "# Gaps — Test Feature" in body_content
        assert len(body_content.strip()) > 0

    def test_cli_fails_on_missing_source_file(self, feature_dir):
        """CLI exits non-zero if a source file does not exist."""
        output_file = feature_dir / "TestPlanGaps.md"
        nonexistent_file = feature_dir / ".gaps-nonexistent.md"

        feature_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "consolidate_gaps.py"),
            "--feature-name",
            "Test Feature",
            "--source",
            f"endpoints={nonexistent_file}",
            "--out",
            str(output_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=REPO_ROOT)

        stdout_data = json.loads(result.stdout)
        assert stdout_data["error"] == "source_file_not_found"
        assert stdout_data["status"] == "failed"

        assert result.returncode != 0, "Should fail when source file does not exist"


class TestConsolidateGapsDocResolutionReRun:
    """Test the doc-resolution RE-RUN workflow: regenerate body + gap_count, then re-set frontmatter."""

    def test_doc_resolution_rerun_workflow(self, feature_dir):
        """
        Integration test simulating the item-6 doc-resolution RE-RUN flow:
        1. Initial run: endpoints has API-spec gap, infra has design-doc gap → gap_count=2, status=Open
        2. Set frontmatter with those values
        3. RE-RUN: API-spec doc provided (endpoints now "No gaps"), infra still has design-doc gap
           → gap_count=1, body no longer contains "API spec" but still contains "design doc"
        4. Re-set frontmatter with new values → gap_count=1, status=Open
        5. RE-RUN: infra also resolved → gap_count=0, status=Resolved
        """
        feature_dir.mkdir(parents=True, exist_ok=True)

        # --- Step 1: Initial run with 2 gaps ---
        endpoints_file = feature_dir / ".analysis-endpoints.md"
        infra_file = feature_dir / ".analysis-infra.md"
        output_file = feature_dir / "TestPlanGaps.md"

        initial_endpoints = """## Test Tools

- pytest

## Gaps

- **Catalog endpoint request/response schema is undefined** — would be resolved by: API spec
"""
        initial_infra = """## Gaps

- **Database failover behavior is not documented** — would be resolved by: design doc
"""

        endpoints_file.write_text(initial_endpoints)
        infra_file.write_text(initial_infra)

        cmd_initial = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "consolidate_gaps.py"),
            "--feature-name",
            "Test Feature",
            "--source",
            f"endpoints={endpoints_file}",
            "--source",
            f"infra={infra_file}",
            "--out",
            str(output_file),
        ]

        result_initial = subprocess.run(cmd_initial, capture_output=True, text=True, check=True, cwd=REPO_ROOT)
        initial_json = json.loads(result_initial.stdout)

        assert initial_json["gap_count"] == 2
        assert initial_json["status"] == "Open"

        # --- Step 2: Set frontmatter with initial values ---
        cmd_set_initial = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "frontmatter.py"),
            "set",
            str(output_file),
            "feature=Test Feature",
            "source_key=RHAISTRAT-400",
            f"status={initial_json['status']}",
            f"gap_count={initial_json['gap_count']}",
        ]

        subprocess.run(cmd_set_initial, capture_output=True, text=True, check=True, cwd=REPO_ROOT)

        # Read back gap_count and status
        cmd_read_gap_count = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "frontmatter.py"),
            "read",
            str(output_file),
            "gap_count",
        ]
        cmd_read_status = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "frontmatter.py"),
            "read",
            str(output_file),
            "status",
        ]

        result_gap_count = subprocess.run(cmd_read_gap_count, capture_output=True, text=True, check=True, cwd=REPO_ROOT)
        result_status = subprocess.run(cmd_read_status, capture_output=True, text=True, check=True, cwd=REPO_ROOT)

        assert result_gap_count.stdout.strip() == "2"
        assert result_status.stdout.strip() == "Open"

        # --- Step 3: RE-RUN with API-spec gap resolved ---
        rerun_endpoints = """## Gaps

No gaps identified.
"""

        endpoints_file.write_text(rerun_endpoints)
        # infra_file unchanged (still has design-doc gap)

        cmd_rerun1 = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "consolidate_gaps.py"),
            "--feature-name",
            "Test Feature",
            "--source",
            f"endpoints={endpoints_file}",
            "--source",
            f"infra={infra_file}",
            "--out",
            str(output_file),
        ]

        result_rerun1 = subprocess.run(cmd_rerun1, capture_output=True, text=True, check=True, cwd=REPO_ROOT)
        rerun1_json = json.loads(result_rerun1.stdout)

        assert rerun1_json["gap_count"] == 1
        assert rerun1_json["status"] == "Open"

        # Check body: API spec should be gone, design doc should remain
        body_after_rerun1 = output_file.read_text()
        assert "API spec" not in body_after_rerun1, "API spec gap should be removed after re-run"
        assert "design doc" in body_after_rerun1, "design doc gap should still be present"

        # --- Step 4: Re-set frontmatter with new values ---
        cmd_set_rerun1 = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "frontmatter.py"),
            "set",
            str(output_file),
            "feature=Test Feature",
            "source_key=RHAISTRAT-400",
            f"status={rerun1_json['status']}",
            f"gap_count={rerun1_json['gap_count']}",
        ]

        subprocess.run(cmd_set_rerun1, capture_output=True, text=True, check=True, cwd=REPO_ROOT)

        result_gap_count_rerun1 = subprocess.run(
            cmd_read_gap_count, capture_output=True, text=True, check=True, cwd=REPO_ROOT
        )
        result_status_rerun1 = subprocess.run(
            cmd_read_status, capture_output=True, text=True, check=True, cwd=REPO_ROOT
        )

        assert result_gap_count_rerun1.stdout.strip() == "1"
        assert result_status_rerun1.stdout.strip() == "Open"

        # --- Step 5: RE-RUN with all gaps resolved ---
        rerun_infra = """## Gaps

No gaps identified.
"""

        infra_file.write_text(rerun_infra)

        cmd_rerun2 = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "consolidate_gaps.py"),
            "--feature-name",
            "Test Feature",
            "--source",
            f"endpoints={endpoints_file}",
            "--source",
            f"infra={infra_file}",
            "--out",
            str(output_file),
        ]

        result_rerun2 = subprocess.run(cmd_rerun2, capture_output=True, text=True, check=True, cwd=REPO_ROOT)
        rerun2_json = json.loads(result_rerun2.stdout)

        assert rerun2_json["gap_count"] == 0
        assert rerun2_json["status"] == "Resolved"

        # Check body: should say "No gaps identified"
        body_after_rerun2 = output_file.read_text()
        assert "No gaps identified" in body_after_rerun2

        # Re-set frontmatter with final values
        cmd_set_rerun2 = [
            "uv",
            "run",
            "python",
            str(REPO_ROOT / "scripts" / "frontmatter.py"),
            "set",
            str(output_file),
            "feature=Test Feature",
            "source_key=RHAISTRAT-400",
            f"status={rerun2_json['status']}",
            f"gap_count={rerun2_json['gap_count']}",
        ]

        subprocess.run(cmd_set_rerun2, capture_output=True, text=True, check=True, cwd=REPO_ROOT)

        result_gap_count_rerun2 = subprocess.run(
            cmd_read_gap_count, capture_output=True, text=True, check=True, cwd=REPO_ROOT
        )
        result_status_rerun2 = subprocess.run(
            cmd_read_status, capture_output=True, text=True, check=True, cwd=REPO_ROOT
        )

        assert result_gap_count_rerun2.stdout.strip() == "0"
        assert result_status_rerun2.stdout.strip() == "Resolved"
