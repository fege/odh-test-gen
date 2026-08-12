"""Unit tests for scripts/add_jira_labels.py."""

from unittest.mock import patch

import pytest

from scripts.add_jira_labels import main, rubric_label_for_verdict


class TestRubricLabelForVerdict:
    """Tests for rubric_label_for_verdict() pure function."""

    @pytest.mark.parametrize(
        "verdict,expected_label",
        [
            ("Ready", "test-plan-rubric-pass"),
            ("Revise", "test-plan-rubric-revise"),
            ("Rework", "test-plan-rubric-fail"),
            ("Bogus", None),
        ],
    )
    def test_verdict_to_label_mapping(self, verdict, expected_label):
        assert rubric_label_for_verdict(verdict) == expected_label


class TestMain:
    """Tests for main() argument handling and label assembly."""

    @pytest.mark.parametrize(
        "extra_argv,expected_exit,expected_labels,expected_stderr",
        [
            pytest.param(
                ["--verdict", "Ready", "test-plan-auto-revised"],
                0,
                ["test-plan-rubric-pass", "test-plan-auto-revised"],
                None,
                id="verdict_and_literal_combined",
            ),
            pytest.param(
                [],
                1,
                None,
                "No labels to add",
                id="no_verdict_no_labels_is_an_error",
            ),
            pytest.param(
                ["--verdict", "Bogus", "test-plan-auto-revised"],
                0,
                ["test-plan-auto-revised"],
                "Unexpected verdict",
                id="unrecognized_verdict_still_adds_literal_labels",
            ),
            pytest.param(
                ["--verdict", "Bogus"],
                1,
                None,
                "No labels to add",
                id="unrecognized_verdict_with_no_literal_labels_is_an_error",
            ),
        ],
    )
    @patch("scripts.add_jira_labels.add_labels")
    def test_main_label_assembly(
        self, mock_add_labels, monkeypatch, capsys, extra_argv, expected_exit, expected_labels, expected_stderr
    ):
        monkeypatch.setattr("sys.argv", ["add_jira_labels.py", "RHAISTRAT-400", *extra_argv])

        exit_code = main()

        assert exit_code == expected_exit
        if expected_labels is None:
            mock_add_labels.assert_not_called()
        else:
            mock_add_labels.assert_called_once_with("RHAISTRAT-400", expected_labels)
        if expected_stderr is not None:
            assert expected_stderr in capsys.readouterr().err
