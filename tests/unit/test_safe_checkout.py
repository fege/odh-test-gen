"""Test safe_checkout_branch utility."""

from unittest.mock import patch, MagicMock

from scripts.repo import safe_checkout_branch


def test_safe_checkout_refuses_dirty_repo():
    """Verify safe_checkout_branch refuses to checkout when working tree is dirty."""
    with patch("subprocess.run") as mock_run:
        # Mock dirty working tree
        def mock_subprocess(cmd, **kwargs):
            if cmd[:2] == ["git", "status"]:
                return MagicMock(returncode=0, stdout="M  file.txt\n")
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = mock_subprocess

        result = safe_checkout_branch("/test/repo", "test-branch", remote="origin")

        assert result == 1, "Should fail when working tree is dirty"

        # Should NOT call git checkout when dirty
        checkout_calls = [c for c in mock_run.call_args_list if c[0][0][:2] == ["git", "checkout"]]
        assert not checkout_calls, f"Should not checkout dirty repo: {checkout_calls}"


def test_safe_checkout_detects_stale_local_branch():
    """Verify safe_checkout_branch detects and updates stale local branch."""
    with patch("subprocess.run") as mock_run:
        call_count = 0

        def mock_subprocess(cmd, **kwargs):
            nonlocal call_count
            call_count += 1

            if cmd[:2] == ["git", "status"]:
                # Clean working tree
                return MagicMock(returncode=0, stdout="", check=True)
            elif cmd[:2] == ["git", "fetch"]:
                return MagicMock(returncode=0)
            elif cmd[:3] == ["git", "show-ref", "--verify"]:
                # Local branch exists
                return MagicMock(returncode=0)
            elif cmd[:2] == ["git", "rev-parse"]:
                # Return different SHAs to simulate stale branch
                if "origin/" in str(cmd):
                    return MagicMock(returncode=0, stdout="abc123\n")  # Remote SHA
                else:
                    return MagicMock(returncode=0, stdout="def456\n")  # Local SHA (different = stale)
            elif cmd[:2] == ["git", "checkout"]:
                return MagicMock(returncode=0)
            elif cmd[:2] == ["git", "pull"]:
                return MagicMock(returncode=0)
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = mock_subprocess

        result = safe_checkout_branch("/test/repo", "test-branch", remote="origin")

        assert result == 0, "Should succeed"

        # Should call git pull to update stale branch
        pull_calls = [c for c in mock_run.call_args_list if c[0][0][:2] == ["git", "pull"]]
        assert pull_calls, "Should pull to update stale branch"


def test_safe_checkout_creates_tracking_branch_if_not_exists():
    """Verify safe_checkout_branch creates tracking branch if doesn't exist locally."""
    with patch("subprocess.run") as mock_run:

        def mock_subprocess(cmd, **kwargs):
            if cmd[:2] == ["git", "status"]:
                # Clean working tree
                return MagicMock(returncode=0, stdout="")
            elif cmd[:2] == ["git", "fetch"]:
                return MagicMock(returncode=0)
            elif cmd[:3] == ["git", "show-ref", "--verify"]:
                # Local branch doesn't exist
                return MagicMock(returncode=1)
            elif cmd[:2] == ["git", "checkout"]:
                return MagicMock(returncode=0)
            return MagicMock(returncode=0, stdout="")

        mock_run.side_effect = mock_subprocess

        result = safe_checkout_branch("/test/repo", "new-branch", remote="origin")

        assert result == 0, "Should succeed"

        # Should call git checkout -b to create tracking branch
        checkout_calls = [c for c in mock_run.call_args_list if c[0][0][:2] == ["git", "checkout"]]
        assert any("-b" in str(c) for c in checkout_calls), "Should create tracking branch with -b"
        assert any("origin/new-branch" in str(c) for c in checkout_calls), "Should track remote branch"
