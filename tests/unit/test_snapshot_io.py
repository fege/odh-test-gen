"""Unit tests for scripts/utils/snapshot_io.py — symlink-safe I/O primitives and the
feature-dir containment policy for strategy snapshots.
"""

import os
import re
import stat

import pytest

from scripts.utils.snapshot_io import (
    read_file_nofollow,
    require_feature_snapshot,
    require_within_feature_dir,
    write_snapshot_nofollow,
)


class TestReadFileNofollow:
    def test_reads_regular_file(self, tmp_path):
        target = tmp_path / "regular.md"
        target.write_text("hello world")

        assert read_file_nofollow(target) == "hello world"

    def test_rejects_symlink_to_regular_file(self, tmp_path):
        target = tmp_path / "real.md"
        target.write_text("secret")
        link = tmp_path / "link.md"
        link.symlink_to(target)

        with pytest.raises(OSError):
            read_file_nofollow(link)


class TestWriteSnapshotNofollow:
    def test_writes_new_file_with_mode_0600(self, tmp_path):
        target = tmp_path / "snapshot.md"

        write_snapshot_nofollow(target, "content")

        assert target.read_text() == "content"
        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    def test_overwrites_existing_regular_file(self, tmp_path):
        target = tmp_path / "snapshot.md"
        target.write_text("old")

        write_snapshot_nofollow(target, "new")

        assert target.read_text() == "new"

    def test_enforces_mode_0600_on_preexisting_file(self, tmp_path):
        target = tmp_path / "snapshot.md"
        target.write_text("old")
        target.chmod(0o644)

        write_snapshot_nofollow(target, "new")

        assert stat.S_IMODE(target.stat().st_mode) == 0o600

    def test_rejects_preexisting_symlink_to_regular_file(self, tmp_path):
        real = tmp_path / "victim.md"
        real.write_text("must not be overwritten")
        link = tmp_path / "snapshot.md"
        link.symlink_to(real)

        with pytest.raises(OSError):
            write_snapshot_nofollow(link, "attack payload")

        assert real.read_text() == "must not be overwritten"

    def test_rejects_dangling_symlink(self, tmp_path):
        link = tmp_path / "dangling.md"
        link.symlink_to(tmp_path / "nonexistent.md")

        with pytest.raises(OSError):
            write_snapshot_nofollow(link, "attack payload")


class TestRequireFeatureSnapshot:
    def test_accepts_source_strategy_inside_feature_dir(self, tmp_path):
        snapshot = tmp_path / ".source-strategy.md"
        snapshot.write_text("content")

        result = require_feature_snapshot(tmp_path, snapshot)

        assert result == snapshot.resolve()

    def test_rejects_wrong_filename(self, tmp_path):
        wrong_name = tmp_path / "strategy.md"
        wrong_name.write_text("content")

        with pytest.raises(ValueError, match=re.escape("snapshot filename must be .source-strategy.md")):
            require_feature_snapshot(tmp_path, wrong_name)

    def test_rejects_path_escaping_feature_dir(self, tmp_path):
        outer = tmp_path / "outer"
        outer.mkdir()
        inner = tmp_path / "inner"
        inner.mkdir()
        snapshot = outer / ".source-strategy.md"
        snapshot.write_text("content")

        with pytest.raises(ValueError, match="not inside feature_dir"):
            require_feature_snapshot(inner, snapshot)

    def test_rejects_traversal_escape(self, tmp_path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        secret = tmp_path / ".source-strategy.md"
        secret.write_text("top secret")

        with pytest.raises(ValueError, match="not inside feature_dir"):
            require_feature_snapshot(feature_dir, feature_dir / ".." / ".source-strategy.md")

    def test_rejects_fifo_snapshot(self, tmp_path):
        fifo = tmp_path / ".source-strategy.md"
        os.mkfifo(fifo)

        with pytest.raises(ValueError, match="not a regular file"):
            require_feature_snapshot(tmp_path, fifo)


class TestRequireWithinFeatureDir:
    def test_rejects_directory(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with pytest.raises(ValueError, match="not_regular_file"):
            require_within_feature_dir(tmp_path, subdir)
