"""Unit tests for scripts/resolve_design_spec.py."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.resolve_design_spec import (
    DESIGN_SPEC_SNAPSHOT,
    classify_companion_doc,
    looks_like_design_spec,
    main,
    resolve_design_spec,
    select_design_spec_attachment,
    snapshot_design_spec,
)

ISSUE_KEY = "RHAISTRAT-400"


def _attachment(
    filename,
    *,
    created="2026-09-01T12:00:00.000+0000",
    attachment_id="1",
    content="https://jira.example/1",
):
    return {
        "filename": filename,
        "created": created,
        "id": attachment_id,
        "content": content,
    }


class TestLooksLikeDesignSpec:
    def test_filename_match(self):
        assert looks_like_design_spec("RHAISTRAT-400-design-spec.md")
        assert looks_like_design_spec("design_spec.md")
        assert looks_like_design_spec("./docs/Design-Spec.md")

    def test_heading_match(self):
        assert looks_like_design_spec("notes.md", "# Design Spec: Create subscription\n")
        assert not looks_like_design_spec("notes.md", "# Something else\n")

    def test_non_match(self):
        assert not looks_like_design_spec("adr.pdf")
        assert not looks_like_design_spec("api-spec.md")


class TestClassifyCompanionDoc:
    def test_design_spec_by_name(self):
        assert classify_companion_doc("design-spec.md") == "design_spec"

    def test_adr_by_name(self):
        assert classify_companion_doc("my-adr.pdf") == "adr"

    def test_adr_by_heading(self, tmp_path):
        doc = tmp_path / "notes.md"
        doc.write_text("# Architecture Decision Record\n\nContext\n", encoding="utf-8")
        content = doc.read_text(encoding="utf-8")
        assert classify_companion_doc(doc, content) == "adr"

    def test_other(self):
        assert classify_companion_doc("api-openapi.yaml") == "other"


class TestSelectDesignSpecAttachment:
    def test_exact_name_preferred(self):
        attachments = [
            _attachment("other-design-spec.md", content="https://jira.example/fallback"),
            _attachment(f"{ISSUE_KEY}-design-spec.md", content="https://jira.example/exact"),
        ]
        selected = select_design_spec_attachment(ISSUE_KEY, attachments)
        assert selected["content"] == "https://jira.example/exact"

    def test_fallback_design_spec_filename(self):
        attachments = [
            _attachment("notes.md", content="https://jira.example/notes"),
            _attachment("feature-design-spec.md", content="https://jira.example/fallback"),
        ]
        selected = select_design_spec_attachment(ISSUE_KEY, attachments)
        assert selected["content"] == "https://jira.example/fallback"

    def test_newest_wins(self):
        attachments = [
            _attachment(
                f"{ISSUE_KEY}-design-spec.md",
                created="2026-09-01T10:00:00.000+0000",
                attachment_id="1",
                content="https://jira.example/older",
            ),
            _attachment(
                f"{ISSUE_KEY}-design-spec.md",
                created="2026-09-02T10:00:00.000+0000",
                attachment_id="2",
                content="https://jira.example/newer",
            ),
        ]
        selected = select_design_spec_attachment(ISSUE_KEY, attachments)
        assert selected["content"] == "https://jira.example/newer"

    def test_none_found(self):
        attachments = [_attachment("RHAISTRAT-400-strategy.md")]
        assert select_design_spec_attachment(ISSUE_KEY, attachments) is None


class TestResolveDesignSpec:
    def test_local_path_wins_over_attachments(self, tmp_path):
        doc = tmp_path / "design-spec.md"
        doc.write_text("# Design Spec: Demo\n", encoding="utf-8")
        result = resolve_design_spec(
            issue_key=ISSUE_KEY,
            local_path=str(doc),
            attachments=[_attachment(f"{ISSUE_KEY}-design-spec.md")],
            fetch_issue=False,
        )
        assert result["source"] == "local"
        assert result["kind"] == "design_spec"
        assert "Design Spec: Demo" in result["content"]

    def test_local_path_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            resolve_design_spec(local_path=str(tmp_path / "missing.md"), fetch_issue=False)

    def test_local_path_symlink_rejected(self, tmp_path):
        target = tmp_path / "secret.md"
        target.write_text("secret", encoding="utf-8")
        link = tmp_path / "design-spec.md"
        link.symlink_to(target)
        with pytest.raises(OSError, match="local_path_is_symlink"):
            resolve_design_spec(local_path=str(link), fetch_issue=False)

    def test_attachment_download(self):
        attachments = [_attachment(f"{ISSUE_KEY}-design-spec.md", content="https://jira.example/ds")]
        result = resolve_design_spec(
            issue_key=ISSUE_KEY,
            attachments=attachments,
            attachment_downloader=lambda url: f"body from {url}",
            fetch_issue=False,
        )
        assert result["source"] == "attachment"
        assert result["content"] == "body from https://jira.example/ds"
        assert result["filename"] == f"{ISSUE_KEY}-design-spec.md"

    def test_none_when_no_attachment(self):
        result = resolve_design_spec(
            issue_key=ISSUE_KEY,
            attachments=[],
            fetch_issue=False,
        )
        assert result == {"status": "ok", "source": "none", "content": None}


class TestSnapshotDesignSpec:
    def test_writes_snapshot(self, tmp_path):
        path = snapshot_design_spec(str(tmp_path), "# Design Spec\n")
        assert Path(path).name == DESIGN_SPEC_SNAPSHOT
        assert Path(path).read_text(encoding="utf-8") == "# Design Spec\n"

    def test_rejects_symlinked_feature_dir(self, tmp_path):
        real = tmp_path / "outside"
        real.mkdir()
        link = tmp_path / "feature"
        link.symlink_to(real)
        with pytest.raises(OSError, match="feature_dir_is_symlink"):
            snapshot_design_spec(str(link), "# Design Spec\n")
        assert not (real / DESIGN_SPEC_SNAPSHOT).exists()

    def test_rejects_symlinked_feature_dir_parent(self, tmp_path):
        real = tmp_path / "outside"
        real.mkdir()
        plans_link = tmp_path / "plans"
        plans_link.symlink_to(real)
        feature_dir = plans_link / "feature"
        with pytest.raises(OSError, match="feature_dir_is_symlink"):
            snapshot_design_spec(str(feature_dir), "# Design Spec\n")
        assert not (real / "feature" / DESIGN_SPEC_SNAPSHOT).exists()


class TestResolveDesignSpecCli:
    def test_cli_local_snapshot(self, tmp_path, capsys):
        doc = tmp_path / "design-spec.md"
        doc.write_text("# Design Spec: CLI\n", encoding="utf-8")
        feature_dir = tmp_path / "feature"
        feature_dir.mkdir()

        with patch.object(
            sys,
            "argv",
            [
                "resolve_design_spec.py",
                "--issue-key",
                ISSUE_KEY,
                "--local-path",
                str(doc),
                "--feature-dir",
                str(feature_dir),
                "--snapshot",
            ],
        ):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["source"] == "local"
        assert out["has_content"] is True
        assert out["additional_docs_entry"] == DESIGN_SPEC_SNAPSHOT
        assert (feature_dir / DESIGN_SPEC_SNAPSHOT).is_file()

    def test_cli_attachments_json(self, tmp_path, capsys):
        attachments_file = tmp_path / "attachments.json"
        attachments_file.write_text(
            json.dumps([_attachment(f"{ISSUE_KEY}-design-spec.md", content="https://jira.example/ds")]),
            encoding="utf-8",
        )

        with patch(
            "scripts.resolve_design_spec.download_attachment",
            return_value="# Design Spec from attachment\n",
        ):
            with patch.object(
                sys,
                "argv",
                [
                    "resolve_design_spec.py",
                    "--issue-key",
                    ISSUE_KEY,
                    "--attachments-json",
                    str(attachments_file),
                ],
            ):
                with pytest.raises(SystemExit) as exc:
                    main()
        assert exc.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["source"] == "attachment"
        assert out["has_content"] is True

    def test_cli_attachments_json_invalid_shape(self, tmp_path, capsys):
        attachments_file = tmp_path / "attachments.json"
        attachments_file.write_text(json.dumps("invalid"), encoding="utf-8")

        with patch.object(
            sys,
            "argv",
            [
                "resolve_design_spec.py",
                "--issue-key",
                ISSUE_KEY,
                "--attachments-json",
                str(attachments_file),
            ],
        ):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "attachments_json_invalid_shape"

    def test_cli_attachments_json_non_utf8(self, tmp_path, capsys):
        attachments_file = tmp_path / "attachments.json"
        attachments_file.write_bytes(b'[{"filename": "\xff-design-spec.md"}]')

        with patch.object(
            sys,
            "argv",
            [
                "resolve_design_spec.py",
                "--issue-key",
                ISSUE_KEY,
                "--attachments-json",
                str(attachments_file),
            ],
        ):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "attachments_json_unreadable"

    def test_cli_classify(self, tmp_path, capsys):
        doc = tmp_path / "design-spec.md"
        doc.write_text("# Design Spec: Demo\n", encoding="utf-8")

        with patch.object(sys, "argv", ["resolve_design_spec.py", "--classify", str(doc)]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["kind"] == "design_spec"

    def test_cli_classify_adr_pdf_without_reading(self, tmp_path, capsys):
        pdf = tmp_path / "my-adr.pdf"
        pdf.write_bytes(b"%PDF-1.4 binary \xff\xfe content")

        with patch.object(sys, "argv", ["resolve_design_spec.py", "--classify", str(pdf)]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["kind"] == "adr"

    def test_cli_classify_binary_other_returns_json_error(self, tmp_path, capsys):
        blob = tmp_path / "notes.bin"
        blob.write_bytes(b"\xff\xfe binary without utf-8")

        with patch.object(sys, "argv", ["resolve_design_spec.py", "--classify", str(blob)]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "local_path_unreadable"

    def test_cli_classify_symlink_rejected(self, tmp_path, capsys):
        target = tmp_path / "secret.md"
        target.write_text("secret", encoding="utf-8")
        link = tmp_path / "design-spec.md"
        link.symlink_to(target)

        with patch.object(sys, "argv", ["resolve_design_spec.py", "--classify", str(link)]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "local_path_is_symlink"

    def test_cli_snapshot_symlinked_feature_dir_rejected(self, tmp_path, capsys):
        doc = tmp_path / "design-spec.md"
        doc.write_text("# Design Spec: CLI\n", encoding="utf-8")
        real = tmp_path / "outside"
        real.mkdir()
        feature_dir = tmp_path / "feature"
        feature_dir.symlink_to(real)

        with patch.object(
            sys,
            "argv",
            [
                "resolve_design_spec.py",
                "--issue-key",
                ISSUE_KEY,
                "--local-path",
                str(doc),
                "--feature-dir",
                str(feature_dir),
                "--snapshot",
            ],
        ):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == "feature_dir_is_symlink"
        assert not (real / DESIGN_SPEC_SNAPSHOT).exists()
