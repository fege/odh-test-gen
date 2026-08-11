"""Unit tests for scripts/resolve_additional_docs.py — deterministic resolution of
additional_docs from TestPlan.md frontmatter with symlink-safe containment.
"""

import json
import sys

import pytest

from scripts.resolve_additional_docs import main, resolve_additional_docs


def _write_testplan(path, additional_docs=None):
    """Write a minimal TestPlan.md with the given additional_docs frontmatter field."""
    lines = [
        "---",
        "feature: Test",
        "source_key: RHAISTRAT-400",
        "version: 1.0.0",
        "status: Draft",
        "last_updated: 2026-08-11",
        "author: QE Team",
    ]
    if additional_docs is not None:
        lines.append("additional_docs:")
        for doc in additional_docs:
            lines.append(f"  - {doc}")
    lines.append("---")
    lines.append("")
    lines.append("# Test Plan")
    lines.append("")
    path.write_text("\n".join(lines))


class TestResolveAdditionalDocs:
    def test_local_path_inside_feature_dir_is_read(self, tmp_path):
        doc = tmp_path / "spec.md"
        doc.write_text("API specification content")
        _write_testplan(tmp_path / "TestPlan.md", additional_docs=["spec.md"])

        result = resolve_additional_docs(str(tmp_path))

        assert result["status"] == "ok"
        assert len(result["docs"]) == 1
        entry = result["docs"][0]
        assert entry["ref"] == "spec.md"
        assert entry["kind"] == "local"
        assert entry["status"] == "read"
        assert entry["content"] == "API specification content"

    def test_absolute_path_is_skipped(self, tmp_path):
        _write_testplan(tmp_path / "TestPlan.md", additional_docs=["/etc/passwd"])

        result = resolve_additional_docs(str(tmp_path))

        assert result["status"] == "ok"
        assert len(result["docs"]) == 1
        entry = result["docs"][0]
        assert entry["kind"] == "local"
        assert entry["status"] == "skipped"
        assert entry["reason"] == "absolute_path"
        assert "content" not in entry

    def test_traversal_escaping_feature_dir_is_skipped(self, tmp_path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        secret = tmp_path / "secret.env"
        secret.write_text("SECRET=leaked")
        _write_testplan(feature_dir / "TestPlan.md", additional_docs=["../secret.env"])

        result = resolve_additional_docs(str(feature_dir))

        assert result["status"] == "ok"
        assert len(result["docs"]) == 1
        entry = result["docs"][0]
        assert entry["kind"] == "local"
        assert entry["status"] == "skipped"
        assert entry["reason"] == "traversal"
        assert "content" not in entry
        # Must not leak absolute paths or the file content.
        assert str(tmp_path) not in json.dumps(entry)
        assert "SECRET" not in json.dumps(entry)

    def test_symlink_pointing_outside_feature_dir_is_skipped(self, tmp_path):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        real_file = outside / "doc.md"
        real_file.write_text("outside content")
        link = feature_dir / "doc.md"
        link.symlink_to(real_file)
        _write_testplan(feature_dir / "TestPlan.md", additional_docs=["doc.md"])

        result = resolve_additional_docs(str(feature_dir))

        assert result["status"] == "ok"
        entry = result["docs"][0]
        assert entry["status"] == "skipped"
        # resolve() dereferences the symlink; containment sees it outside feature_dir.
        assert entry["reason"] == "outside_feature_dir"
        assert "content" not in entry

    def test_symlink_to_target_inside_feature_dir_is_still_skipped(self, tmp_path):
        """A symlink whose target is INSIDE feature_dir is still rejected — pins the
        is_symlink() branch in require_within_feature_dir (mirrors the
        test_rejects_symlink_to_target_inside_feature_dir test for build_citation_inputs).
        """
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        real_file = feature_dir / "real-doc.md"
        real_file.write_text("real content")
        link = feature_dir / "linked-doc.md"
        link.symlink_to(real_file)
        _write_testplan(feature_dir / "TestPlan.md", additional_docs=["linked-doc.md"])

        result = resolve_additional_docs(str(feature_dir))

        assert result["status"] == "ok"
        entry = result["docs"][0]
        assert entry["status"] == "skipped"
        assert entry["reason"] == "symlink"
        assert "content" not in entry

    def test_url_entry_is_passed_through_never_read(self, tmp_path):
        _write_testplan(
            tmp_path / "TestPlan.md",
            additional_docs=["https://docs.google.com/document/d/abc123"],
        )

        result = resolve_additional_docs(str(tmp_path))

        assert result["status"] == "ok"
        assert len(result["docs"]) == 1
        entry = result["docs"][0]
        assert entry["ref"] == "https://docs.google.com/document/d/abc123"
        assert entry["kind"] == "url"
        assert "content" not in entry
        assert "status" not in entry

    def test_http_url_is_classified_as_url(self, tmp_path):
        _write_testplan(tmp_path / "TestPlan.md", additional_docs=["http://example.com/spec"])

        result = resolve_additional_docs(str(tmp_path))

        assert result["docs"][0]["kind"] == "url"

    def test_empty_additional_docs_returns_empty_list(self, tmp_path):
        _write_testplan(tmp_path / "TestPlan.md", additional_docs=[])

        result = resolve_additional_docs(str(tmp_path))

        assert result == {"status": "ok", "docs": []}

    def test_missing_additional_docs_field_returns_empty_list(self, tmp_path):
        _write_testplan(tmp_path / "TestPlan.md")  # no additional_docs

        result = resolve_additional_docs(str(tmp_path))

        assert result == {"status": "ok", "docs": []}

    @pytest.mark.parametrize(
        "content,exc_type,match",
        [
            (None, FileNotFoundError, None),
            (
                "---\nfeature: Test\nsource_key: K\nversion: 1.0.0\n"
                "status: Draft\nlast_updated: 2026-08-11\nauthor: QE\n"
                "additional_docs: spec.md\n---\n\n# Test Plan\n",
                ValueError,
                "invalid_additional_docs",
            ),
            ("---\nadditional_docs: [\n---\n\n# Test Plan\n", ValueError, "invalid_frontmatter"),
        ],
        ids=["missing_testplan", "scalar_additional_docs", "malformed_yaml"],
    )
    def test_invalid_input_raises(self, tmp_path, content, exc_type, match):
        if content is not None:
            (tmp_path / "TestPlan.md").write_text(content)

        with pytest.raises(exc_type, match=match):
            resolve_additional_docs(str(tmp_path))

    def test_nonexistent_local_file_is_skipped_unreadable(self, tmp_path):
        _write_testplan(tmp_path / "TestPlan.md", additional_docs=["does_not_exist.md"])

        result = resolve_additional_docs(str(tmp_path))

        entry = result["docs"][0]
        assert entry["status"] == "skipped"
        assert entry["reason"] == "unreadable"

    def test_subdirectory_path_inside_feature_dir_is_read(self, tmp_path):
        sub = tmp_path / "docs"
        sub.mkdir()
        doc = sub / "api-spec.md"
        doc.write_text("endpoint details")
        _write_testplan(tmp_path / "TestPlan.md", additional_docs=["docs/api-spec.md"])

        result = resolve_additional_docs(str(tmp_path))

        entry = result["docs"][0]
        assert entry["status"] == "read"
        assert entry["content"] == "endpoint details"

    def test_mixed_entries_classified_correctly(self, tmp_path):
        (tmp_path / "local.md").write_text("local content")
        _write_testplan(
            tmp_path / "TestPlan.md",
            additional_docs=[
                "local.md",
                "https://docs.google.com/doc/123",
                "/etc/shadow",
                "../escape.md",
            ],
        )

        result = resolve_additional_docs(str(tmp_path))

        assert len(result["docs"]) == 4
        assert result["docs"][0]["kind"] == "local"
        assert result["docs"][0]["status"] == "read"
        assert result["docs"][1]["kind"] == "url"
        assert result["docs"][2]["status"] == "skipped"
        assert result["docs"][2]["reason"] == "absolute_path"
        assert result["docs"][3]["status"] == "skipped"
        assert result["docs"][3]["reason"] == "traversal"


class TestResolveAdditionalDocsCLI:
    def test_ok_path_exits_zero_with_structured_json(self, tmp_path, capsys):
        (tmp_path / "spec.md").write_text("spec content")
        _write_testplan(tmp_path / "TestPlan.md", additional_docs=["spec.md"])

        old_argv = sys.argv
        try:
            sys.argv = ["resolve_additional_docs.py", str(tmp_path)]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit")
        finally:
            sys.argv = old_argv

        output = json.loads(capsys.readouterr().out)
        assert output["status"] == "ok"
        assert output["docs"][0]["status"] == "read"

    def test_missing_testplan_exits_one_with_error_json(self, tmp_path, capsys):
        old_argv = sys.argv
        try:
            sys.argv = ["resolve_additional_docs.py", str(tmp_path)]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 1
            else:
                raise AssertionError("main() must exit with code 1")
        finally:
            sys.argv = old_argv

        raw_output = capsys.readouterr().out
        output = json.loads(raw_output)
        assert output == {"status": "error", "error": "testplan_not_found"}
        # Must not leak absolute paths in the error output.
        assert str(tmp_path) not in raw_output

    def test_empty_additional_docs_exits_zero(self, tmp_path, capsys):
        _write_testplan(tmp_path / "TestPlan.md")

        old_argv = sys.argv
        try:
            sys.argv = ["resolve_additional_docs.py", str(tmp_path)]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit")
        finally:
            sys.argv = old_argv

        output = json.loads(capsys.readouterr().out)
        assert output == {"status": "ok", "docs": []}

    def test_traversal_cli_does_not_leak_absolute_path(self, tmp_path, capsys):
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()
        (tmp_path / "secret.env").write_text("SECRET=value")
        _write_testplan(feature_dir / "TestPlan.md", additional_docs=["../secret.env"])

        old_argv = sys.argv
        try:
            sys.argv = ["resolve_additional_docs.py", str(feature_dir)]
            try:
                main()
            except SystemExit as exc:
                assert exc.code == 0
            else:
                raise AssertionError("main() must exit")
        finally:
            sys.argv = old_argv

        raw_output = capsys.readouterr().out
        output = json.loads(raw_output)
        assert output["docs"][0]["reason"] == "traversal"
        # No absolute path leakage.
        assert str(tmp_path) not in raw_output
        assert "SECRET" not in raw_output
