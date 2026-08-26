#!/usr/bin/env python3
"""Load calibration example files from core/, optional ui/, and optional team directories.

Usage:
    python scripts/load_calibration.py <calibration_dir> \
        [--include-teams=ai_hub,model_serving] \
        [--framework pytest]

Output (JSON):
    {
        "files": [{"path": "core/01-example.md", "source": "core"}, ...],
        "file_count": 1,
        "calibration_text": "## From core/01-example.md\\n\\n...",
        "warnings": []
    }

Load order is core → ui (if present) → --include-teams. ``source`` is ``core``, ``ui``,
or ``team:<name>``. Reserved names ``core`` and ``ui`` are not treated as team names.

Exit 1 with {"error": "..."} when the calibration dir or core/ is missing, core has no
eligible files before --framework filtering, or a file cannot be read. Missing optional
ui/ is not an error.

When --framework is set, the filter runs after core, ui, and teams are loaded. Exit 0 with
empty files, file_count 0, calibration_text "", and a warnings entry only when no loaded file
in any layer matches (for example Cypress files in ui/ with pytest-only core).
"""

import argparse
import json
import re
import sys
from pathlib import Path

from scripts.utils.validation_config_loader import parse_teams_arg

README_FILENAME = "README.md"
ELIGIBLE_SUFFIXES = {".md", ".py", ".go", ".ts", ".tsx"}
SKIPPED_NAMES = {README_FILENAME}
CORE_SOURCE = "core"
UI_SOURCE = "ui"
RESERVED_DIR_NAMES = {CORE_SOURCE, UI_SOURCE}


def _is_eligible_file(path: Path) -> bool:
    """Return True if path is a calibration file (suffix and skip-list only)."""
    if not path.is_file() or path.name in SKIPPED_NAMES:
        return False
    return path.suffix in ELIGIBLE_SUFFIXES


def _matches_framework(path: Path, framework: str | None) -> bool:
    """Return True if path should be kept under an optional --framework filter.

    The framework string must appear as a whole token in the filename (split on
    non-alphanumerics, case-insensitive). ``go`` matches ``good-go-test.go`` but
    not ``good-pytest-test.py``.
    """
    if not framework:
        return True
    tokens = [part.lower() for part in re.split(r"[^A-Za-z0-9]+", path.name) if part]
    return framework.lower() in tokens


def _sorted_eligible_files(directory: Path, resolved_root: Path) -> list[Path]:
    """Return eligible files in directory, sorted by filename.

    After eligibility, each path must resolve under ``resolved_root``. A symlink or
    file that resolves outside raises ValueError before any caller reads the file.
    """
    eligible = []
    for path in directory.iterdir():
        if not _is_eligible_file(path):
            continue
        resolved = path.resolve()
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(f"Calibration file {path} resolves outside calibration directory {resolved_root}") from exc
        eligible.append(path)
    return sorted(eligible, key=lambda path: path.name)


def _append_layer(
    entries: list[dict],
    seen_basenames: set[str],
    directory: Path,
    source: str,
    resolved_root: Path,
) -> None:
    """Append files from directory (filename-sorted), skipping duplicate basenames."""
    for path in _sorted_eligible_files(directory, resolved_root):
        if path.name in seen_basenames:
            continue
        entries.append({"path": f"{source}/{path.name}", "source": source, "abs_path": path})
        seen_basenames.add(path.name)


def load_calibration(calibration_dir, teams=None, framework=None) -> dict:
    """Load calibration files from core/, optional ui/, and optional team directories.

    Args:
        calibration_dir: Path to the calibration root (contains required core/).
        teams: Optional team names whose directories are loaded after core and ui.
            ``core`` and ``ui`` are reserved and ignored as team names.
        framework: If set, only include files whose filename has this string as a
            whole token (non-alphanumeric split, case-insensitive). Applied after
            combining layers; empty core is judged before this filter.

    Returns:
        Dict with files, file_count, calibration_text, and warnings.

    Raises:
        FileNotFoundError: calibration_dir or core/ is missing.
        ValueError: core/ has no eligible files before --framework filtering,
            a team name is empty/whitespace, a team path resolves outside
            the calibration directory, or an eligible file resolves outside
            the calibration directory.
        OSError, UnicodeError: a selected file cannot be read as UTF-8.
    """
    root = Path(calibration_dir)
    resolved_root = root.resolve()
    framework_token = framework.strip() if framework else None

    if not root.exists():
        raise FileNotFoundError(f"Calibration directory not found: {root}")

    core_dir = root / CORE_SOURCE
    if not core_dir.is_dir():
        raise FileNotFoundError(f"Core calibration directory not found: {core_dir}")

    core_files = _sorted_eligible_files(core_dir, resolved_root)
    if not core_files:
        raise ValueError(f"Core calibration directory is empty (no eligible files): {core_dir}")

    entries: list[dict] = []
    seen_basenames: set[str] = set()
    warnings: list[str] = []

    for path in core_files:
        entries.append({"path": f"{CORE_SOURCE}/{path.name}", "source": CORE_SOURCE, "abs_path": path})
        seen_basenames.add(path.name)

    ui_dir = root / UI_SOURCE
    if ui_dir.is_dir():
        _append_layer(entries, seen_basenames, ui_dir, UI_SOURCE, resolved_root)

    for team in teams or []:
        if team in RESERVED_DIR_NAMES:
            continue
        if not team.strip():
            raise ValueError(f"Team name {team!r} is empty or whitespace-only")
        team_dir = (root / team).resolve()
        try:
            team_dir.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(f"Team '{team}' resolves outside calibration directory {resolved_root}") from exc
        if not team_dir.is_dir():
            warnings.append(f"Calibration directory for team '{team}' not found at {team_dir}; skipping team files.")
            continue
        for path in _sorted_eligible_files(team_dir, resolved_root):
            if path.name in seen_basenames:
                continue
            entries.append({"path": f"{team}/{path.name}", "source": f"team:{team}", "abs_path": path})
            seen_basenames.add(path.name)

    if framework_token:
        entries = [entry for entry in entries if _matches_framework(entry["abs_path"], framework_token)]

    if not entries:
        if framework_token:
            warnings.append(f"No calibration files matched --framework={framework_token} under {root}")
            return {
                "files": [],
                "file_count": 0,
                "calibration_text": "",
                "warnings": warnings,
            }
        raise ValueError(f"No calibration files found under {root}")

    text_parts = []
    files_out = []
    for entry in entries:
        content = entry["abs_path"].read_text(encoding="utf-8")
        text_parts.append(f"## From {entry['path']}\n\n{content}")
        files_out.append({"path": entry["path"], "source": entry["source"]})

    return {
        "files": files_out,
        "file_count": len(files_out),
        "calibration_text": "\n\n".join(text_parts),
        "warnings": warnings,
    }


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Load calibration example files from core/, ui/, and team directories",
    )
    parser.add_argument("calibration_dir", help="Path to calibration directory (must contain core/)")
    parser.add_argument(
        "--include-teams",
        default="",
        help="Comma-separated team names to load examples from (not core or ui)",
    )
    parser.add_argument(
        "--framework",
        default=None,
        help="Only include files whose filename has this framework as a whole token (e.g. pytest)",
    )

    args = parser.parse_args()

    try:
        result = load_calibration(
            args.calibration_dir,
            teams=parse_teams_arg(args.include_teams),
            framework=args.framework,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
