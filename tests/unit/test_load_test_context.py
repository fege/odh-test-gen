"""Unit tests for scripts/load_test_context.py CLI."""

import json

from scripts.load_test_context import main


def _write_context(odh_root, repo_name, payload):
    tests_dir = odh_root / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / f"{repo_name}.json").write_text(json.dumps(payload))


class TestLoadTestContextCLI:
    def test_org_repo_loads_context_and_writes_file(self, tmp_path, run_cli):
        odh = tmp_path / "odh-test-context"
        payload = {"testing": {"framework": "pytest"}, "container_recipe": {"base_image": "ubi"}}
        _write_context(odh, "opendatahub-tests", payload)
        feature = tmp_path / "feature"
        feature.mkdir()

        exit_code, data = run_cli(
            main,
            ["opendatahub-io/opendatahub-tests", str(odh), str(feature)],
        )

        assert exit_code == 0
        assert data["target_repo_name"] == "opendatahub-tests"
        assert data["use_odh_context"] is True
        assert data["test_context"] == payload
        saved = json.loads((feature / ".test_implementation_context.json").read_text())
        assert saved == payload

    def test_local_path_derives_repo_name(self, tmp_path, run_cli):
        odh = tmp_path / "odh-test-context"
        _write_context(odh, "opendatahub-tests", {"testing": {"framework": "pytest"}})
        feature = tmp_path / "feature"
        feature.mkdir()

        exit_code, data = run_cli(main, [str(tmp_path / "opendatahub-tests"), str(odh), str(feature)])

        assert exit_code == 0
        assert data["target_repo_name"] == "opendatahub-tests"
        assert data["use_odh_context"] is True
        assert (feature / ".test_implementation_context.json").exists()

    def test_missing_context_is_json_null(self, tmp_path, run_cli):
        odh = tmp_path / "odh-test-context"
        (odh / "tests").mkdir(parents=True)
        feature = tmp_path / "feature"
        feature.mkdir()

        exit_code, data = run_cli(main, ["opendatahub-tests", str(odh), str(feature)])

        assert exit_code == 0
        assert data["use_odh_context"] is False
        assert data["test_context"] is None
        assert not (feature / ".test_implementation_context.json").exists()
