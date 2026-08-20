"""Unit tests for scripts/ensure_feature_test_dir.py."""

import subprocess

import pytest

from scripts.ensure_feature_test_dir import ensure_feature_test_dir, resolve_feature_package_name
from tests.helpers import write_valid_testplan


def _feature_dir(tmp_path, feature: str = "nemo_guardrails_runtime_state_api"):
    feature_dir = tmp_path / "plan" / feature
    feature_dir.mkdir(parents=True)
    write_valid_testplan(feature_dir / "TestPlan.md", feature=feature)
    return feature_dir


def _component_dir(tmp_path, *, package: bool = True):
    parent = tmp_path / "tests" / "ai_safety"
    parent.mkdir(parents=True)
    if package:
        (parent / "__init__.py").write_text("")
    return parent


class TestResolveFeaturePackageName:
    def test_uses_testplan_feature(self, tmp_path):
        feature_dir = _feature_dir(tmp_path, "nemo_guardrails_runtime_state_api")
        assert resolve_feature_package_name(str(feature_dir)) == "nemo_guardrails_runtime_state_api"

    def test_sanitizes_feature(self, tmp_path):
        feature_dir = _feature_dir(tmp_path, "Hello World")
        assert resolve_feature_package_name(str(feature_dir)) == "hello_world"

    def test_falls_back_to_directory_basename(self, tmp_path):
        feature_dir = tmp_path / "plan" / "from_basename"
        feature_dir.mkdir(parents=True)
        assert resolve_feature_package_name(str(feature_dir)) == "from_basename"


class TestEnsureFeatureTestDir:
    def test_creates_missing_package_and_init(self, tmp_path):
        feature_dir = _feature_dir(tmp_path)
        parent = _component_dir(tmp_path)

        result = ensure_feature_test_dir(str(feature_dir), str(tmp_path), "tests/ai_safety")

        dest = parent / "nemo_guardrails_runtime_state_api"
        assert result == "tests/ai_safety/nemo_guardrails_runtime_state_api"
        assert dest.is_dir()
        assert (dest / "__init__.py").is_file()

    def test_creates_dir_without_init_when_parent_is_not_a_package(self, tmp_path):
        feature_dir = _feature_dir(tmp_path)
        parent = _component_dir(tmp_path, package=False)

        ensure_feature_test_dir(str(feature_dir), str(tmp_path), "tests/ai_safety")

        dest = parent / "nemo_guardrails_runtime_state_api"
        assert dest.is_dir()
        assert not (dest / "__init__.py").exists()

    def test_reuses_existing_package(self, tmp_path):
        feature_dir = _feature_dir(tmp_path)
        parent = _component_dir(tmp_path)
        dest = parent / "nemo_guardrails_runtime_state_api"
        dest.mkdir()
        marker = dest / "already_there.py"
        marker.write_text("keep")
        (dest / "__init__.py").write_text("# custom\n")

        result = ensure_feature_test_dir(str(feature_dir), str(tmp_path), "tests/ai_safety")

        assert result == "tests/ai_safety/nemo_guardrails_runtime_state_api"
        assert marker.read_text() == "keep"
        assert (dest / "__init__.py").read_text() == "# custom\n"

    def test_does_not_nest_when_test_dir_already_is_the_feature_package(self, tmp_path):
        feature_dir = _feature_dir(tmp_path)
        already = tmp_path / "tests" / "ai_safety" / "nemo_guardrails_runtime_state_api"
        already.mkdir(parents=True)

        result = ensure_feature_test_dir(
            str(feature_dir),
            str(tmp_path),
            "tests/ai_safety/nemo_guardrails_runtime_state_api",
        )

        assert result == "tests/ai_safety/nemo_guardrails_runtime_state_api"
        assert not (already / "nemo_guardrails_runtime_state_api").exists()

    def test_existing_dir_without_init_is_left_alone(self, tmp_path):
        feature_dir = _feature_dir(tmp_path)
        parent = _component_dir(tmp_path)
        dest = parent / "nemo_guardrails_runtime_state_api"
        dest.mkdir()

        ensure_feature_test_dir(str(feature_dir), str(tmp_path), "tests/ai_safety")

        assert dest.is_dir()
        assert not (dest / "__init__.py").exists()

    def test_does_not_reuse_a_differently_named_sibling(self, tmp_path):
        feature_dir = _feature_dir(tmp_path)
        parent = _component_dir(tmp_path)
        (parent / "nemo_guardrails").mkdir()

        result = ensure_feature_test_dir(str(feature_dir), str(tmp_path), "tests/ai_safety")

        assert result == "tests/ai_safety/nemo_guardrails_runtime_state_api"
        assert (parent / "nemo_guardrails_runtime_state_api").is_dir()
        assert (parent / "nemo_guardrails").is_dir()

    def test_missing_parent_errors(self, tmp_path):
        feature_dir = _feature_dir(tmp_path)
        with pytest.raises(FileNotFoundError, match="does not exist"):
            ensure_feature_test_dir(str(feature_dir), str(tmp_path), "tests/ai_safety")

    def test_existing_file_at_package_path_errors(self, tmp_path):
        feature_dir = _feature_dir(tmp_path)
        parent = _component_dir(tmp_path)
        (parent / "nemo_guardrails_runtime_state_api").write_text("not a dir")

        with pytest.raises(NotADirectoryError):
            ensure_feature_test_dir(str(feature_dir), str(tmp_path), "tests/ai_safety")

    @pytest.mark.parametrize(
        "test_dir",
        [
            "../evil_outside",
            "/tmp/evil",
            "tests/../../outside",
            "tests/../../../tmp",
        ],
    )
    def test_rejects_path_traversal(self, tmp_path, test_dir):
        """test_dir with parent refs or absolute paths must not create files outside repo."""
        feature_dir = _feature_dir(tmp_path)
        _component_dir(tmp_path)
        # Create plausible outside dirs so paths resolve successfully
        (tmp_path / "evil_outside").mkdir(exist_ok=True)
        (tmp_path / "outside").mkdir(exist_ok=True)

        # Should reject with either "must be relative" (absolute) or "escapes target repo" (.. traversal)
        with pytest.raises(ValueError, match="(must be relative|escapes target repo)"):
            ensure_feature_test_dir(str(feature_dir), str(tmp_path), test_dir)

    def test_accepts_deep_nested_relative_path(self, tmp_path):
        """Valid deep relative paths within repo must work."""
        feature_dir = _feature_dir(tmp_path)
        deep = tmp_path / "tests" / "integration" / "ai_safety"
        deep.mkdir(parents=True)
        (deep / "__init__.py").write_text("")

        result = ensure_feature_test_dir(str(feature_dir), str(tmp_path), "tests/integration/ai_safety")

        assert result == "tests/integration/ai_safety/nemo_guardrails_runtime_state_api"
        assert (deep / "nemo_guardrails_runtime_state_api").is_dir()


def test_cli_prints_path(tmp_path):
    feature_dir = _feature_dir(tmp_path)
    _component_dir(tmp_path)

    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/ensure_feature_test_dir.py",
            str(feature_dir),
            str(tmp_path),
            "tests/ai_safety",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "tests/ai_safety/nemo_guardrails_runtime_state_api"


def test_cli_rejects_missing_args():
    result = subprocess.run(
        ["uv", "run", "python", "scripts/ensure_feature_test_dir.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Usage:" in result.stderr
