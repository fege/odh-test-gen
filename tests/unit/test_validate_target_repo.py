"""
Unit tests for validate_target_repo.py functions.
"""

import pytest

from scripts.validate_target_repo import (
    extract_target_repo_from_args,
    get_default_target_repo,
    validate_target_repo,
    validate_target_repo_path,
)


class TestGetDefaultTargetRepo:
    """Test get_default_target_repo function."""

    def test_returns_opendatahub_tests(self):
        """Test that default is opendatahub-io/opendatahub-tests."""
        assert get_default_target_repo() == "opendatahub-io/opendatahub-tests"


class TestExtractTargetRepoFromArgs:
    """Test extract_target_repo_from_args function."""

    @pytest.mark.parametrize(
        "args_string,expected",
        [
            ("", None),
            ("feature/path", None),
            ("--target-repo opendatahub-io/notebooks", "opendatahub-io/notebooks"),
            ("feature/path --target-repo opendatahub-io/model-registry", "opendatahub-io/model-registry"),
            ("--test-cases TC-001 --target-repo opendatahub-io/dashboard", "opendatahub-io/dashboard"),
            ("--target-repo ~/my-path/opendatahub-tests --other-flag", "~/my-path/opendatahub-tests"),
        ],
    )
    def test_extracts_target_repo_value(self, args_string, expected):
        """Test extraction of --target-repo value from various argument patterns."""
        result = extract_target_repo_from_args(args_string)
        assert result == expected


class TestValidateTargetRepo:
    """Test validate_target_repo function."""

    @pytest.mark.parametrize(
        "repo_name,valid,expected_repo,error_fragment",
        [
            ("opendatahub-io/opendatahub-tests", True, "opendatahub-io/opendatahub-tests", None),
            ("opendatahub-io/notebooks", True, "opendatahub-io/notebooks", None),
            ("my-org/my-repo", True, "my-org/my-repo", None),
            ("invalid-no-slash", False, None, "org/repo"),
            ("", False, None, "org/repo"),
            ("/no-org", False, None, "org/repo"),
            ("org/", False, None, "org/repo"),
            ("https://github.com/org/repo", True, "org/repo", None),
            ("https://github.com/opendatahub-io/opendatahub-tests", True, "opendatahub-io/opendatahub-tests", None),
            ("http://github.com/my-org/my-repo", True, "my-org/my-repo", None),
            ("my org/repo", False, None, "org/repo"),
            ("org/repo?ref=main", False, None, "org/repo"),
            (
                "https://user:token@github.com/opendatahub-io/opendatahub-tests",
                True,
                "opendatahub-io/opendatahub-tests",
                None,
            ),
        ],
    )
    def test_validates_repo_format(self, repo_name, valid, expected_repo, error_fragment):
        """Test validation of org/repo format and GitHub URLs."""
        result = validate_target_repo(repo_name)
        assert result["valid"] == valid

        if valid:
            assert result["repo"] == expected_repo
            assert "error" not in result
        else:
            assert "error" in result
            if error_fragment:
                assert error_fragment in result["error"]


class TestValidateTargetRepoPath:
    """Test validate_target_repo_path function."""

    @pytest.mark.parametrize(
        "setup,expected_valid,error_fragment",
        [
            (lambda p: (p.mkdir(parents=True, exist_ok=True), (p / ".git").mkdir())[1], True, None),  # Valid git repo
            (lambda p: None, False, "does not exist"),  # Non-existent path
            (lambda p: p.mkdir(parents=True, exist_ok=True), False, "Not a git repository"),  # Dir without .git
        ],
    )
    def test_path_validation(self, tmp_path, setup, expected_valid, error_fragment):
        """Test path validation with various scenarios."""
        test_path = tmp_path / "test_repo"

        if setup:
            setup(test_path)

        result = validate_target_repo_path(str(test_path))

        assert result["valid"] == expected_valid

        if expected_valid:
            assert result["path"] == str(test_path)
        else:
            assert "error" in result
            if error_fragment:
                assert error_fragment in result["error"]


class TestTildeExpansion:
    """Test that ~ paths are expanded before validation."""

    def test_tilde_path_is_expanded(self, tmp_path, monkeypatch):
        """Verify ~ in --target-repo is expanded to the real home directory."""
        fake_home = tmp_path / "fakehome"
        repo = fake_home / "my-repo"
        repo.mkdir(parents=True)
        (repo / ".git").mkdir()

        monkeypatch.setenv("HOME", str(fake_home))

        from scripts.validate_target_repo import main

        captured = []
        monkeypatch.setattr("builtins.print", lambda x: captured.append(x))
        monkeypatch.setattr("sys.argv", ["validate_target_repo.py", "--target-repo", "~/my-repo"])

        main()

        assert len(captured) == 1
        assert captured[0] == str(repo)
        assert "~" not in captured[0]
