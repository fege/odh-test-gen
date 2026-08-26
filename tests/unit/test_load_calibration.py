"""Unit tests for scripts/load_calibration.py."""

from pathlib import Path

import pytest

from scripts.load_calibration import load_calibration, main
from tests.consts.calibration_constants import (
    DUP_CORE_BODY,
    DUP_FILENAME,
    DUP_TEAM_BODY,
    ESCAPE_BODY,
    ESCAPE_FILENAME,
    ESCAPE_OUTSIDE_DIRNAME,
    FRAMEWORK_CORE_FILES,
    FRAMEWORK_CYPRESS,
    FRAMEWORK_CYPRESS_POOR,
    FRAMEWORK_GO,
    FRAMEWORK_GO_TOKEN,
    FRAMEWORK_PYTEST_GOOD,
    FRAMEWORK_PYTEST_POOR,
    FRAMEWORK_UNMATCHED,
    FUNCTION_CALIBRATION_CORE,
    FUNCTION_CALIBRATION_UI,
    FUNCTION_CORE_FORBIDDEN_GLOBS,
    FUNCTION_CORE_PYTEST_GLOB,
    GO_AND_PYTEST_CORE_FILES,
    INVALID_UTF8_CORE_FILENAME,
    MISSING_TEAM_NAME,
    NON_PYTEST_PATH_MARKERS,
    PLAN_CORE_FILES,
    PLAN_CORE_FIRST,
    PLAN_CORE_FIRST_BODY,
    PLAN_CORE_LATER,
    PLAN_CORE_LATER_BODY,
    PYTEST_CORE_FILES,
    README_BODY,
    README_FILENAME,
    REVIEW_CALIBRATION_CORE,
    SYMLINK_OUTSIDE_BODY,
    TEAM_EMPTY,
    TEAM_EXTRA_BODY,
    TEAM_EXTRA_FILENAME,
    TEAM_NAME_AI_HUB,
    TEAM_WHITESPACE,
    UI_CYPRESS_FILES,
    UI_CYPRESS_GOOD_PATH,
    UI_OVERLAY_SOURCE,
    UI_TEAM_FILES,
)
from tests.consts.validation_constants import NON_UTF8_PLAN_BYTES
from tests.helpers import setup_calibration_dir


def _file_paths(result):
    return [entry["path"] for entry in result["files"]]


def _escaped_team_name(tmp_path, escape_kind):
    """Write an eligible .md outside calibration/ and return the team name that would reach it."""
    if escape_kind == "..":
        (tmp_path / ESCAPE_FILENAME).write_text(f"{ESCAPE_BODY}\n")
        return ".."
    if escape_kind == "../outside":
        outside = tmp_path / ESCAPE_OUTSIDE_DIRNAME
        outside.mkdir()
        (outside / ESCAPE_FILENAME).write_text(f"{ESCAPE_BODY}\n")
        return "../outside"
    leaked = tmp_path / "leaked_absolute_team"
    leaked.mkdir()
    (leaked / ESCAPE_FILENAME).write_text(f"{ESCAPE_BODY}\n")
    return str(leaked)


def _assert_warnings(result, *tokens):
    """Success payloads always include a warnings list; tokens must appear when given."""
    warnings = result["warnings"]
    assert isinstance(warnings, list)
    if tokens:
        joined = "\n".join(warnings)
        for token in tokens:
            assert token in joined
    else:
        assert warnings == []


class TestLoadCalibrationCore:
    def test_core_only_sorted_headers_sources_and_concatenated_text(self, tmp_path):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)

        result = load_calibration(calibration_dir)

        _assert_warnings(result)
        assert result["file_count"] == 2
        assert result["files"] == [
            {"path": f"core/{PLAN_CORE_FIRST}", "source": "core"},
            {"path": f"core/{PLAN_CORE_LATER}", "source": "core"},
        ]
        text = result["calibration_text"]
        first_header = f"## From core/{PLAN_CORE_FIRST}"
        later_header = f"## From core/{PLAN_CORE_LATER}"
        assert text.index(first_header) < text.index(later_header)
        assert PLAN_CORE_FIRST_BODY in text.split(first_header, 1)[1]
        assert PLAN_CORE_LATER_BODY in text.split(later_header, 1)[1]

    def test_core_symlink_resolving_outside_calibration_root_raises(self, tmp_path):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)

        core_dir = Path(calibration_dir) / "core"
        outside = tmp_path / "leaked-symlink-target.md"
        outside.write_text(f"{SYMLINK_OUTSIDE_BODY}\n")
        link = core_dir / "leaked-via-symlink.md"
        link.symlink_to(Path("..") / ".." / outside.name)

        with pytest.raises(ValueError) as exc_info:
            load_calibration(calibration_dir)

        assert SYMLINK_OUTSIDE_BODY not in str(exc_info.value)

    def test_skips_readme_md_in_core_and_team_dir(self, tmp_path):
        calibration_dir = setup_calibration_dir(
            tmp_path,
            {**PLAN_CORE_FILES, README_FILENAME: f"{README_BODY}\n"},
            team_files={TEAM_NAME_AI_HUB: {README_FILENAME: f"{README_BODY}\n"}},
        )

        result = load_calibration(calibration_dir, teams=[TEAM_NAME_AI_HUB])

        _assert_warnings(result)
        assert all(Path(path).name != README_FILENAME for path in _file_paths(result))
        assert README_BODY not in result["calibration_text"]
        assert result["file_count"] == 2


class TestLoadCalibrationTeams:
    def test_team_files_are_additive_after_core(self, tmp_path):
        calibration_dir = setup_calibration_dir(
            tmp_path,
            PLAN_CORE_FILES,
            team_files={TEAM_NAME_AI_HUB: {TEAM_EXTRA_FILENAME: f"{TEAM_EXTRA_BODY}\n"}},
        )

        result = load_calibration(calibration_dir, teams=[TEAM_NAME_AI_HUB])

        _assert_warnings(result)
        assert result["files"][-1] == {
            "path": f"{TEAM_NAME_AI_HUB}/{TEAM_EXTRA_FILENAME}",
            "source": f"team:{TEAM_NAME_AI_HUB}",
        }
        assert [entry["source"] for entry in result["files"] if entry["source"] == "core"] == ["core", "core"]
        assert TEAM_EXTRA_BODY in result["calibration_text"]
        assert f"## From {TEAM_NAME_AI_HUB}/{TEAM_EXTRA_FILENAME}" in result["calibration_text"]

    def test_missing_team_directory_warns_and_succeeds(self, tmp_path):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)

        result = load_calibration(calibration_dir, teams=[MISSING_TEAM_NAME])

        assert result["file_count"] == 2
        assert all(entry["source"] == "core" for entry in result["files"])
        _assert_warnings(result, MISSING_TEAM_NAME)

    def test_duplicate_relative_path_core_wins_over_team_copy(self, tmp_path):
        calibration_dir = setup_calibration_dir(
            tmp_path,
            {**PLAN_CORE_FILES, DUP_FILENAME: f"{DUP_CORE_BODY}\n"},
            team_files={TEAM_NAME_AI_HUB: {DUP_FILENAME: f"{DUP_TEAM_BODY}\n"}},
        )

        result = load_calibration(calibration_dir, teams=[TEAM_NAME_AI_HUB])

        _assert_warnings(result)
        paths = _file_paths(result)
        assert f"core/{DUP_FILENAME}" in paths
        assert f"{TEAM_NAME_AI_HUB}/{DUP_FILENAME}" not in paths
        assert DUP_CORE_BODY in result["calibration_text"]
        assert DUP_TEAM_BODY not in result["calibration_text"]

    @pytest.mark.parametrize(
        "escape_kind",
        ["..", "../outside", "leaked_absolute_team"],
    )
    def test_team_path_outside_calibration_root_raises(self, tmp_path, escape_kind):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)
        team = _escaped_team_name(tmp_path, escape_kind)

        with pytest.raises(ValueError, match="resolves outside calibration directory") as exc_info:
            load_calibration(calibration_dir, teams=[team])

        message = str(exc_info.value)
        assert team in message
        assert ESCAPE_BODY not in message

    def test_empty_or_whitespace_team_name_raises(self, tmp_path):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)

        with pytest.raises(ValueError):
            load_calibration(calibration_dir, teams=[TEAM_EMPTY, TEAM_WHITESPACE])


class TestLoadCalibrationUiOverlay:
    def test_ui_files_load_after_core_before_teams(self, tmp_path):
        calibration_dir = setup_calibration_dir(
            tmp_path,
            PLAN_CORE_FILES,
            team_files={
                UI_OVERLAY_SOURCE: {FRAMEWORK_CYPRESS: UI_CYPRESS_FILES[FRAMEWORK_CYPRESS]},
                TEAM_NAME_AI_HUB: {TEAM_EXTRA_FILENAME: f"{TEAM_EXTRA_BODY}\n"},
            },
        )

        result = load_calibration(calibration_dir, teams=[TEAM_NAME_AI_HUB])

        _assert_warnings(result)
        sources = [entry["source"] for entry in result["files"]]
        assert sources == ["core", "core", UI_OVERLAY_SOURCE, f"team:{TEAM_NAME_AI_HUB}"]
        assert result["files"][2] == {"path": UI_CYPRESS_GOOD_PATH, "source": UI_OVERLAY_SOURCE}
        assert f"## From {UI_CYPRESS_GOOD_PATH}" in result["calibration_text"]


class TestLoadCalibrationFramework:
    def test_framework_pytest_includes_pytest_files_only(self, tmp_path):
        calibration_dir = setup_calibration_dir(tmp_path, FRAMEWORK_CORE_FILES)

        result = load_calibration(calibration_dir, framework="pytest")

        _assert_warnings(result)
        names = [Path(path).name for path in _file_paths(result)]
        assert set(names) == {FRAMEWORK_PYTEST_GOOD, FRAMEWORK_PYTEST_POOR}
        assert all("pytest" in name for name in names)
        assert not any(marker in name for name in names for marker in NON_PYTEST_PATH_MARKERS)

    def test_framework_cypress_uses_ui_when_core_is_pytest_only(self, tmp_path):
        calibration_dir = setup_calibration_dir(tmp_path, PYTEST_CORE_FILES, team_files=UI_TEAM_FILES)

        result = load_calibration(calibration_dir, framework="cypress")

        _assert_warnings(result)
        assert result["file_count"] == 2
        assert all(entry["source"] == UI_OVERLAY_SOURCE for entry in result["files"])
        paths = _file_paths(result)
        assert UI_CYPRESS_GOOD_PATH in paths
        assert f"{UI_OVERLAY_SOURCE}/{FRAMEWORK_CYPRESS_POOR}" in paths
        names = [Path(path).name for path in paths]
        assert all("cypress" in name for name in names)
        assert not any("pytest" in name for name in names)

    def test_framework_go_is_whole_token_not_substring_of_good(self, tmp_path):
        calibration_dir = setup_calibration_dir(tmp_path, GO_AND_PYTEST_CORE_FILES)

        result = load_calibration(calibration_dir, framework=FRAMEWORK_GO_TOKEN)

        _assert_warnings(result)
        names = {Path(path).name for path in _file_paths(result)}
        assert names == {FRAMEWORK_GO}
        assert FRAMEWORK_PYTEST_GOOD not in names


class TestLoadCalibrationCli:
    def test_cli_core_only_happy_path(self, tmp_path, run_cli):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)

        exit_code, data = run_cli(main, [calibration_dir])

        assert exit_code == 0
        _assert_warnings(data)
        assert data["file_count"] == 2
        assert data["files"][0] == {"path": f"core/{PLAN_CORE_FIRST}", "source": "core"}
        assert f"## From core/{PLAN_CORE_FIRST}" in data["calibration_text"]
        assert PLAN_CORE_FIRST_BODY in data["calibration_text"]

    @pytest.mark.parametrize(
        "kind",
        ["missing_calibration_dir", "missing_core", "empty_core"],
    )
    def test_cli_fail_closed_exits_one_with_json_error(self, tmp_path, run_cli, kind):
        if kind == "missing_calibration_dir":
            args = [str(tmp_path / "no_such_calibration")]
        elif kind == "missing_core":
            calibration_dir = tmp_path / "calibration"
            calibration_dir.mkdir()
            args = [str(calibration_dir)]
        else:
            # Empty before --framework filter, even if ui/ has matching files.
            args = [setup_calibration_dir(tmp_path, {}, team_files=UI_TEAM_FILES)]

        exit_code, data = run_cli(main, args)

        assert exit_code == 1
        assert "error" in data
        assert isinstance(data["error"], str)
        assert data["error"]

    @pytest.mark.parametrize(
        "escape_kind",
        ["..", "../outside", "leaked_absolute_team"],
    )
    def test_cli_team_path_outside_calibration_root_exits_one_with_json_error(self, tmp_path, run_cli, escape_kind):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)
        team = _escaped_team_name(tmp_path, escape_kind)

        exit_code, data = run_cli(main, [calibration_dir, f"--include-teams={team}"])

        assert exit_code == 1
        assert "error" in data
        assert isinstance(data["error"], str)
        assert data["error"]
        assert team in data["error"]
        assert ESCAPE_BODY not in data["error"]
        assert ESCAPE_BODY not in data.get("calibration_text", "")

    def test_cli_missing_team_stdout_is_json_with_warnings(self, tmp_path, run_cli):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)

        exit_code, data = run_cli(main, [calibration_dir, f"--include-teams={MISSING_TEAM_NAME}"])

        assert exit_code == 0
        assert data["file_count"] == 2
        _assert_warnings(data, MISSING_TEAM_NAME)

    def test_cli_unmatched_framework_exits_zero_with_empty_payload(self, tmp_path, run_cli):
        calibration_dir = setup_calibration_dir(tmp_path, PYTEST_CORE_FILES)

        exit_code, data = run_cli(main, [calibration_dir, f"--framework={FRAMEWORK_UNMATCHED}"])

        assert exit_code == 0
        assert data["files"] == []
        assert data["file_count"] == 0
        assert data["calibration_text"] == ""
        names = [Path(path).name for path in _file_paths(data)]
        assert not any("pytest" in name for name in names)
        _assert_warnings(data, FRAMEWORK_UNMATCHED)

    def test_cli_non_utf8_file_in_core_exits_one_with_json_error(self, tmp_path, run_cli):
        calibration_dir = setup_calibration_dir(tmp_path, PLAN_CORE_FILES)
        (Path(calibration_dir) / "core" / INVALID_UTF8_CORE_FILENAME).write_bytes(NON_UTF8_PLAN_BYTES)

        exit_code, data = run_cli(main, [calibration_dir])

        assert exit_code == 1
        assert "error" in data
        assert isinstance(data["error"], str)
        assert data["error"]


class TestProductionCalibrationLayout:
    def test_review_calibration_core_has_markdown(self):
        md_files = [path for path in REVIEW_CALIBRATION_CORE.glob("*.md") if path.is_file()]
        assert md_files, f"expected at least one *.md under {REVIEW_CALIBRATION_CORE}"

    def test_function_calibration_core_is_pytest_without_go_or_spec_tsx(self):
        pytest_files = [path for path in FUNCTION_CALIBRATION_CORE.glob(FUNCTION_CORE_PYTEST_GLOB) if path.is_file()]
        assert pytest_files, f"expected pytest calibration files under {FUNCTION_CALIBRATION_CORE}"
        forbidden = []
        for pattern in FUNCTION_CORE_FORBIDDEN_GLOBS:
            forbidden.extend(path for path in FUNCTION_CALIBRATION_CORE.glob(pattern) if path.is_file())
        assert not forbidden, f"core must not contain {FUNCTION_CORE_FORBIDDEN_GLOBS}: {forbidden}"

    def test_function_calibration_ui_has_cypress_pair(self):
        good = FUNCTION_CALIBRATION_UI / FRAMEWORK_CYPRESS
        poor = FUNCTION_CALIBRATION_UI / FRAMEWORK_CYPRESS_POOR
        assert good.is_file(), f"expected {FRAMEWORK_CYPRESS} under {FUNCTION_CALIBRATION_UI}"
        assert poor.is_file(), f"expected {FRAMEWORK_CYPRESS_POOR} under {FUNCTION_CALIBRATION_UI}"
