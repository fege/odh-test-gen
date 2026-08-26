"""Integration tests for load_calibration.py against shipped calibration trees."""

from pathlib import Path

from scripts.load_calibration import main
from tests.consts.calibration_constants import (
    FRAMEWORK_CYPRESS,
    FRAMEWORK_CYPRESS_POOR,
    FRAMEWORK_PYTEST_GOOD,
    FRAMEWORK_PYTEST_POOR,
    FUNCTION_CALIBRATION_DIR,
    MIN_PLAN_CALIBRATION_FILES,
    NON_PYTEST_PATH_MARKERS,
    PLAN_CALIBRATION_PHRASE,
    PLAN_KAGENTI_FILENAME,
    REVIEW_CALIBRATION_DIR,
    UI_OVERLAY_SOURCE,
)


class TestLoadCalibrationPlanTreeCLI:
    """CLI against the real test-plan-review calibration tree."""

    def test_shipped_review_calibration_loads(self, run_cli):
        """Plan calibration dir loads core markdown examples without snapshotting text."""
        exit_code, data = run_cli(main, [str(REVIEW_CALIBRATION_DIR)])

        assert exit_code == 0
        assert data["warnings"] == []
        assert data["file_count"] >= MIN_PLAN_CALIBRATION_FILES
        paths = [entry["path"] for entry in data["files"]]
        assert any(PLAN_KAGENTI_FILENAME in path for path in paths)
        assert PLAN_CALIBRATION_PHRASE in data["calibration_text"]


class TestLoadCalibrationFunctionTreeCLI:
    """CLI against the real test-plan-score-test-function calibration tree."""

    def test_shipped_function_calibration_filters_pytest(self, run_cli):
        """--framework=pytest includes both pytest pairs and excludes other frameworks."""
        exit_code, data = run_cli(main, [str(FUNCTION_CALIBRATION_DIR), "--framework=pytest"])

        assert exit_code == 0
        assert data["warnings"] == []
        paths = [entry["path"] for entry in data["files"]]
        assert any(FRAMEWORK_PYTEST_GOOD in path for path in paths)
        assert any(FRAMEWORK_PYTEST_POOR in path for path in paths)
        names = [Path(path).name for path in paths]
        assert not any(marker in name for name in names for marker in NON_PYTEST_PATH_MARKERS)

    def test_shipped_function_calibration_filters_cypress(self, run_cli):
        """--framework=cypress loads ui/ Cypress pairs and excludes pytest filenames."""
        exit_code, data = run_cli(main, [str(FUNCTION_CALIBRATION_DIR), "--framework=cypress"])

        assert exit_code == 0
        assert data["warnings"] == []
        paths = [entry["path"] for entry in data["files"]]
        assert any(FRAMEWORK_CYPRESS in path for path in paths)
        assert any(FRAMEWORK_CYPRESS_POOR in path for path in paths)
        assert all(path.startswith(f"{UI_OVERLAY_SOURCE}/") for path in paths)
        names = [Path(path).name for path in paths]
        assert all("cypress" in name for name in names)
        assert not any("pytest" in name for name in names)
