"""Integration contracts for skill helper paths under Fullsend-style delivery."""

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHING_SKILL = "test-plan-publish"
STRATEGY_CONTENT = "# Local strategy fixture\n"

SHELL_BLOCK_RE = re.compile(r"(?ms)^\x60\x60\x60(?:bash|sh|shell)\b[^\n]*\n(.*?)^\x60\x60\x60")
GIT_SKILL_ROOT_RE = re.compile(r"\bgit\s+-C\s+['\"]?\$\{?CLAUDE_SKILL_DIR\}?['\"]?\s+rev-parse\s+--show-toplevel\b")
SCRIPT_COMMAND_PATH_RE = re.compile(
    r"(?<![\w./-])((?:skills/[A-Za-z0-9_.-]+/)?scripts/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.(?:py|sh))"
)


def _tracked_paths(repository: Path) -> tuple[Path, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository,
        capture_output=True,
        check=True,
    )
    return tuple(Path(os.fsdecode(raw_path)) for raw_path in result.stdout.split(b"\0") if raw_path)


def _tree_entries(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_symlink() or path.is_file()}


def _copy_tracked_checkout(source: Path, target: Path) -> set[str]:
    """Copy tracked working-tree contents while excluding Git metadata and untracked local state."""
    target.mkdir(parents=True)
    expected: set[str] = set()

    for relative_path in _tracked_paths(source):
        source_path = source / relative_path
        target_path = target / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if source_path.is_symlink():
            target_path.symlink_to(os.readlink(source_path), target_is_directory=source_path.is_dir())
        elif source_path.is_file():
            shutil.copy2(source_path, target_path)
        else:
            raise AssertionError(f"Tracked checkout entry is missing or unsupported: {relative_path}")

        expected.add(relative_path.as_posix())

    return expected


def _initialize_git_repository(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--quiet"], cwd=path, capture_output=True, check=True)
    return path.resolve()


def _shell_blocks(document: Path) -> list[str]:
    return [match.group(1) for match in SHELL_BLOCK_RE.finditer(document.read_text(encoding="utf-8"))]


def _non_publishing_skill_docs(repository: Path) -> list[Path]:
    return [
        document
        for document in sorted((repository / "skills").glob("*/SKILL.md"))
        if document.parent.name != PUBLISHING_SKILL
    ]


def _find_shell_block(document: Path, needle: str) -> str:
    for block in _shell_blocks(document):
        if needle in block:
            return block
    raise AssertionError(f"No shell command block in {document} contains {needle!r}")


@pytest.fixture
def staged_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "target-workspace"
    expected = _copy_tracked_checkout(REPO_ROOT, workspace)

    assert _tree_entries(workspace) == expected
    assert (workspace / "pyproject.toml").is_file()
    assert not (workspace / ".git").exists()
    assert not (workspace / ".git").is_symlink()
    assert not (workspace / ".venv").exists()

    symlinks = [Path(relative_path) for relative_path in expected if (workspace / relative_path).is_symlink()]
    assert symlinks, "The staged checkout must preserve the repository's tracked helper symlinks"
    for relative_path in symlinks:
        resolved = (workspace / relative_path).resolve(strict=True)
        assert resolved.is_relative_to(workspace.resolve()), f"Symlink escapes staged checkout: {relative_path}"

    return workspace


def _write_uv_stub(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    implementation = bin_dir / "uv_stub.py"
    implementation.write_text(
        """import json
import os
import sys

arguments = sys.argv[1:]
with open(os.environ["UV_CALL_LOG"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps({"cwd": os.getcwd(), "arguments": arguments}) + "\\n")

if arguments == ["sync", "--extra", "dev"]:
    raise SystemExit(0)

if len(arguments) >= 3 and arguments[:2] == ["run", "python"]:
    project_root = os.environ.get("UV_STUB_PROJECT_ROOT", os.getcwd())
    run_environment = os.environ.copy()
    python_path = run_environment.get("PYTHONPATH", "")
    run_environment["PYTHONPATH"] = project_root + (os.pathsep + python_path if python_path else "")
    python = run_environment["PYTHON_BIN"]
    os.execve(python, [python, *arguments[2:]], run_environment)

raise SystemExit(23)
""",
        encoding="utf-8",
    )

    launcher = bin_dir / "uv"
    launcher.write_text(
        f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(implementation))} "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)


def _run_bash(command: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", command],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def _json_result_and_caller_cwd(result: subprocess.CompletedProcess[str], caller: Path) -> dict:
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    json_text, marker, caller_cwd = result.stdout.rpartition("CALLER_CWD=")
    assert marker, f"helper command did not report the caller cwd: {result.stdout}"
    assert Path(caller_cwd.strip()).resolve() == caller.resolve()
    return json.loads(json_text.strip())


def test_no_git_target_workspace_executes_selected_helper_from_unrelated_git_caller(
    staged_workspace: Path, tmp_path: Path
) -> None:
    caller = _initialize_git_repository(tmp_path / "unrelated-caller")
    caller_root = subprocess.run(
        ["git", "-C", str(caller), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert Path(caller_root).resolve() == caller
    assert not staged_workspace.resolve().is_relative_to(caller)

    skill_dir = staged_workspace / "skills" / "test-plan-create"
    selected_helper = skill_dir / "scripts" / "parse_strat.py"
    assert selected_helper.is_file()
    assert selected_helper.resolve(strict=True) == (staged_workspace / "scripts" / "parse_strat.py").resolve()

    env = os.environ.copy()
    env["CLAUDE_SKILL_DIR"] = str(skill_dir)
    env["PYTHONPATH"] = str(staged_workspace) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    result = subprocess.run(
        [sys.executable, str(selected_helper), "new-strat-tmp"],
        cwd=caller,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    payload = json.loads(result.stdout)
    assert payload["created"] is True
    strategy_file = Path(payload["strategy_file"]).resolve()
    temp_root = (staged_workspace / "artifacts" / "strat-tasks" / ".tmp").resolve()
    assert strategy_file.parent == temp_root
    assert strategy_file.is_file()
    assert not (caller / "artifacts").exists()


def test_non_publishing_skill_shell_commands_do_not_discover_package_root_with_git() -> None:
    offenders = [
        f"{document.relative_to(REPO_ROOT)}: {match.group(0)}"
        for document in _non_publishing_skill_docs(REPO_ROOT)
        for block in _shell_blocks(document)
        for match in GIT_SKILL_ROOT_RE.finditer(block)
    ]

    assert not offenders, (
        f"Non-publishing skill command blocks must resolve the package root without Git metadata; found: {offenders}"
    )


def test_non_publishing_skill_script_paths_stay_inside_no_git_workspace(staged_workspace: Path) -> None:
    documents = _non_publishing_skill_docs(staged_workspace)
    assert documents

    reference_count = 0
    for document in documents:
        shell_code = "\n".join(_shell_blocks(document))
        for relative_path in sorted(set(SCRIPT_COMMAND_PATH_RE.findall(shell_code))):
            reference_count += 1
            command_path = staged_workspace / relative_path
            assert command_path.is_file(), (
                f"{document.relative_to(staged_workspace)} references missing {relative_path}"
            )
            resolved = command_path.resolve(strict=True)
            assert resolved.is_relative_to(staged_workspace.resolve()), (
                f"{document.relative_to(staged_workspace)} references a helper outside the staged checkout: "
                f"{relative_path}"
            )

    assert reference_count > 0, "The skill command-path matrix must inspect at least one helper reference"


def test_legacy_installed_plugin_keeps_bootstrap_cache_and_external_output_from_unrelated_cwd(
    tmp_path: Path,
) -> None:
    plugin_root = tmp_path / "installed-plugin"
    _copy_tracked_checkout(REPO_ROOT, plugin_root)
    _initialize_git_repository(plugin_root)
    caller = _initialize_git_repository(tmp_path / "unrelated-caller")

    skill_dir = plugin_root / "skills" / "test-plan-create"
    selected_helper = skill_dir / "scripts" / "parse_strat.py"
    assert selected_helper.is_file()

    log_path = tmp_path / "uv-calls.jsonl"
    bin_dir = tmp_path / "bin"
    _write_uv_stub(bin_dir)

    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_SKILL_DIR": str(skill_dir),
            "PYTHON_BIN": sys.executable,
            "PYTHONPATH": str(plugin_root) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""),
            "SELECTED_HELPER": str(selected_helper),
            "UV_CALL_LOG": str(log_path),
            "UV_STUB_PROJECT_ROOT": str(plugin_root),
            "PATH": str(bin_dir) + os.pathsep + env.get("PATH", ""),
        }
    )

    bootstrap = _find_shell_block(skill_dir / "SKILL.md", "uv sync --extra dev")
    bootstrap_result = _run_bash(
        bootstrap + '\nprintf "CALLER_CWD=%s\\n" "$PWD"\n',
        cwd=caller,
        env=env,
    )
    assert bootstrap_result.returncode == 0, f"stdout:\n{bootstrap_result.stdout}\nstderr:\n{bootstrap_result.stderr}"
    assert bootstrap_result.stdout.strip() == f"CALLER_CWD={caller}"

    resolved_plugin_root = subprocess.run(
        ["git", "-C", str(skill_dir), "rev-parse", "--show-toplevel"],
        cwd=caller,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    assert Path(resolved_plugin_root).resolve() == plugin_root.resolve()

    temp_result = _run_bash(
        'repo_root=$(git -C "$CLAUDE_SKILL_DIR" rev-parse --show-toplevel)\n'
        'tmp_result=$(cd "$repo_root" && uv run python scripts/parse_strat.py new-strat-tmp)\n'
        'printf "%s\\n" "$tmp_result"\n'
        'printf "CALLER_CWD=%s\\n" "$PWD"\n',
        cwd=caller,
        env=env,
    )
    temp_payload = _json_result_and_caller_cwd(temp_result, caller)
    assert temp_payload["created"] is True
    temp_strategy = Path(temp_payload["strategy_file"]).resolve()
    assert temp_strategy.parent == (plugin_root / "artifacts" / "strat-tasks" / ".tmp").resolve()

    cache_dir = plugin_root / "artifacts" / "strat-tasks"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_strategy = cache_dir / "RHAISTRAT-987654.md"
    cached_strategy.write_text(STRATEGY_CONTENT, encoding="utf-8")

    output_dir = tmp_path / "external plan output"
    feature_dir = output_dir / "legacy_feature"
    temp_strategy.write_text(STRATEGY_CONTENT, encoding="utf-8")
    env.update(
        {
            "FEATURE_DIR": str(feature_dir),
            "STRATEGY_FILE": str(temp_strategy),
        }
    )

    snapshot_result = _run_bash(
        'repo_root=$(git -C "$CLAUDE_SKILL_DIR" rev-parse --show-toplevel)\n'
        'snapshot_result=$(cd "$repo_root" && uv run python scripts/parse_strat.py '
        'save-snapshot "$STRATEGY_FILE" "$FEATURE_DIR")\n'
        'printf "%s\\n" "$snapshot_result"\n'
        'printf "CALLER_CWD=%s\\n" "$PWD"\n',
        cwd=caller,
        env=env,
    )
    snapshot_payload = _json_result_and_caller_cwd(snapshot_result, caller)
    assert snapshot_payload["status"] == "ok"
    assert snapshot_payload["source"] == "temp"
    assert Path(snapshot_payload["strategy_file"]).resolve() == (feature_dir / ".source-strategy.md").resolve()
    assert (feature_dir / ".source-strategy.md").read_text(encoding="utf-8") == STRATEGY_CONTENT
    assert json.loads((feature_dir / ".test-plan-output-dir.json").read_text(encoding="utf-8")) == {
        "output_dir": str(output_dir.resolve())
    }
    assert not temp_strategy.exists()

    cache_result = _run_bash(
        'repo_root=$(git -C "$CLAUDE_SKILL_DIR" rev-parse --show-toplevel)\n'
        'cache_result=$(cd "$repo_root" && uv run python scripts/parse_strat.py resolve-local RHAISTRAT-987654)\n'
        'printf "%s\\n" "$cache_result"\n'
        'printf "CALLER_CWD=%s\\n" "$PWD"\n',
        cwd=caller,
        env=env,
    )
    cache_payload = _json_result_and_caller_cwd(cache_result, caller)
    assert cache_payload["found"] is True
    assert Path(cache_payload["strategy_file"]).resolve() == cached_strategy.resolve()
    assert output_dir.is_dir()
    assert not (caller / "artifacts").exists()

    calls = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [(Path(call["cwd"]), call["arguments"]) for call in calls] == [
        (plugin_root.resolve(), ["sync", "--extra", "dev"]),
        (plugin_root.resolve(), ["run", "python", "scripts/parse_strat.py", "new-strat-tmp"]),
        (
            plugin_root.resolve(),
            [
                "run",
                "python",
                "scripts/parse_strat.py",
                "save-snapshot",
                str(temp_strategy),
                str(feature_dir),
            ],
        ),
        (
            plugin_root.resolve(),
            ["run", "python", "scripts/parse_strat.py", "resolve-local", "RHAISTRAT-987654"],
        ),
    ]
