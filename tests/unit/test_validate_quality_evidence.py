"""Regression contracts for the deterministic Scope Fidelity and Actionability evidence gate."""

import pytest

from scripts.utils.schemas import TEMPLATE_HEADINGS
from scripts.validate_quality_evidence import validate_actionability, validate_scope_coverage
from tests.consts.validation_constants import (
    ACTIONABILITY_CONCRETE_PROSE_RBAC_PLAN,
    ACTIONABILITY_DELIMITED_DATA_PLACEHOLDER_PLAN,
    ACTIONABILITY_GENERIC_PROSE_RBAC_PLAN,
    ACTIONABILITY_JUSTIFIED_TBD_PLAN,
    ACTIONABILITY_PROSE_RBAC_PLAN,
    ACTIONABILITY_RBAC_WITHOUT_RESOURCE_PLAN,
    ACTIONABILITY_TBD_DATA_PLAN,
    ACTIONABILITY_TBD_UNKNOWN_PLAN,
    FULLY_MAPPED_SCOPE_PLAN,
    NOT_APPLICABLE_NFR_CASES,
    NOT_APPLICABLE_NFR_SECTIONS,
    QUALITY_EVIDENCE_OBJECTIVES_SECTION,
    QUALITY_EVIDENCE_STRATEGY,
    UNMAPPED_SCOPE_CASES,
)


class TestValidateScopeCoverage:
    @pytest.mark.parametrize(
        "section, section_content, expected_text",
        UNMAPPED_SCOPE_CASES,
        ids=("scope", "priorities", "disconnected", "upgrade", "performance", "rbac", "security", "risks"),
    )
    def test_rejects_scope_entries_without_explicit_objective_mapping(
        self, tmp_path, section, section_content, expected_text
    ):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(f"{QUALITY_EVIDENCE_OBJECTIVES_SECTION}\n\n{section_content}\n")

        result = validate_scope_coverage(str(plan), QUALITY_EVIDENCE_STRATEGY)

        assert result["valid"] is False
        assert {
            "section": section,
            "text": expected_text,
            "reason": "no Section 1.3 objective mapping",
        } in result["missing"]

    def test_accepts_explicit_scope_to_objective_to_strategy_mapping(self, tmp_path):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(FULLY_MAPPED_SCOPE_PLAN)

        result = validate_scope_coverage(str(plan), QUALITY_EVIDENCE_STRATEGY)

        assert result == {"valid": True, "missing": [], "unmapped_objectives": []}

    @pytest.mark.parametrize("section", ("1.2", "2.3", "7.1", "7.2", "7.3", "7.4", "7.5"))
    def test_rejects_unmarked_numbered_scope_entry_when_an_earlier_entry_is_marked(self, tmp_path, section):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(
            f"{QUALITY_EVIDENCE_OBJECTIVES_SECTION}\n\n"
            f"{TEMPLATE_HEADINGS[section]}\n\n"
            "1. First scope entry (Objective: #1)\n"
            "2. Second scope entry\n"
        )

        result = validate_scope_coverage(str(plan), QUALITY_EVIDENCE_STRATEGY)

        assert result["valid"] is False
        assert {
            "section": section,
            "text": "Second scope entry",
            "reason": "no Section 1.3 objective mapping",
        } in result["missing"]

    @pytest.mark.parametrize("section", ("1.2", "2.3", "7.1", "7.2", "7.3", "7.4", "7.5"))
    def test_accepts_fully_marked_numbered_scope_entries(self, tmp_path, section):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(
            f"{QUALITY_EVIDENCE_OBJECTIVES_SECTION}\n\n"
            f"{TEMPLATE_HEADINGS[section]}\n\n"
            "1. First scope entry (Objective: #1)\n"
            "2. Second scope entry (Objective: #1)\n"
        )

        result = validate_scope_coverage(str(plan), QUALITY_EVIDENCE_STRATEGY)

        assert result == {"valid": True, "missing": [], "unmapped_objectives": []}

    @pytest.mark.parametrize("section, section_content", NOT_APPLICABLE_NFR_CASES, ids=NOT_APPLICABLE_NFR_SECTIONS)
    def test_accepts_ungrounded_not_applicable_nfr_entry_without_objective_marker(
        self, tmp_path, section, section_content
    ):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(section_content)

        result = validate_scope_coverage(str(plan), QUALITY_EVIDENCE_STRATEGY)

        assert result == {"valid": True, "missing": [], "unmapped_objectives": []}

    @pytest.mark.parametrize("section", ("1.2", "2.3", "8"))
    def test_rejects_not_applicable_wording_outside_nfr_sections(self, tmp_path, section):
        """The exemption is specific to Section 7.1-7.5; it's not a blanket "Not Applicable" bypass."""
        plan = tmp_path / "TestPlan.md"
        section_body = (
            "| Risk | Impact | Probability | Mitigation |\n"
            "|------|--------|-------------|------------|\n"
            "| **Not Applicable** | Low | Low | No mitigation needed |"
            if section == "8"
            else "**Not Applicable** — this feature has no grounding for this category."
        )
        plan.write_text(f"{QUALITY_EVIDENCE_OBJECTIVES_SECTION}\n\n{TEMPLATE_HEADINGS[section]}\n\n{section_body}\n")

        result = validate_scope_coverage(str(plan), QUALITY_EVIDENCE_STRATEGY)

        assert result["valid"] is False


class TestValidateActionability:
    @pytest.mark.parametrize(
        "plan_content, expected_bare_tbd, expected_missing_detail",
        [
            pytest.param(
                ACTIONABILITY_TBD_UNKNOWN_PLAN,
                "OpenShift version",
                None,
                id="unknown-is-not-a-tbd-resolution-path",
            ),
            pytest.param(
                ACTIONABILITY_TBD_DATA_PLAN,
                None,
                "test data formats and examples",
                id="tbd-format-and-example-are-not-test-data-evidence",
            ),
            pytest.param(
                ACTIONABILITY_PROSE_RBAC_PLAN,
                None,
                "RBAC roles and permissions",
                id="rbac-keywords-without-a-permission-grant-are-insufficient",
            ),
        ],
    )
    def test_rejects_weak_operational_evidence(
        self, tmp_path, plan_content, expected_bare_tbd, expected_missing_detail
    ):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(plan_content)

        result = validate_actionability(str(plan))

        assert result["valid"] is False
        if expected_bare_tbd:
            assert expected_bare_tbd in result["bare_tbd"]
        if expected_missing_detail:
            assert expected_missing_detail in result["missing_details"]

    def test_preserves_tbd_with_an_explicit_resolution_path(self, tmp_path):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(ACTIONABILITY_JUSTIFIED_TBD_PLAN)

        result = validate_actionability(str(plan))

        assert result == {"valid": True, "bare_tbd": [], "missing_details": []}

    def test_rejects_tbd_resolution_without_the_required_label(self, tmp_path):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(ACTIONABILITY_JUSTIFIED_TBD_PLAN.replace("TBD — Resolution: ", "TBD — "))

        result = validate_actionability(str(plan))

        assert result["valid"] is False
        assert "OpenShift version" in result["bare_tbd"]

    @pytest.mark.parametrize(
        "resolution, expected_valid",
        (
            pytest.param("confirm with someone", False, id="generic-unnamed-owner-is-rejected"),
            pytest.param(
                "confirm the version with the test team",
                False,
                id="generic-team-target-is-rejected",
            ),
            pytest.param(
                "confirm the version with the feature owner",
                False,
                id="generic-owner-target-is-rejected",
            ),
            pytest.param("before environment setup", False, id="actionless-concrete-timing-is-rejected"),
            pytest.param("from platform engineering", False, id="actionless-named-owner-is-rejected"),
            pytest.param("from the supported-platform matrix", False, id="actionless-named-source-is-rejected"),
            pytest.param(
                "retrieve the supported-platform matrix from platform engineering before setup.",
                True,
                id="named-owner-is-accepted",
            ),
            pytest.param(
                "confirm the supported version before environment setup.",
                True,
                id="concrete-timing-is-accepted",
            ),
        ),
    )
    def test_tbd_resolution_requires_a_concrete_action_and_target(self, tmp_path, resolution, expected_valid):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(
            ACTIONABILITY_JUSTIFIED_TBD_PLAN.replace(
                "retrieve the supported-platform matrix from platform engineering before setup.", resolution
            )
        )

        result = validate_actionability(str(plan))

        assert result["valid"] is expected_valid
        if not expected_valid:
            assert "OpenShift version" in result["bare_tbd"]

    def test_rejects_rbac_table_permissions_without_a_concrete_resource(self, tmp_path):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(ACTIONABILITY_RBAC_WITHOUT_RESOURCE_PLAN)

        result = validate_actionability(str(plan))

        assert result["valid"] is False
        assert "RBAC roles and permissions" in result["missing_details"]

    @pytest.mark.parametrize(
        "plan_content, expected_valid",
        (
            pytest.param(
                ACTIONABILITY_GENERIC_PROSE_RBAC_PLAN,
                False,
                id="generic-resource-prose-is-insufficient",
            ),
            pytest.param(
                ACTIONABILITY_GENERIC_PROSE_RBAC_PLAN.replace("all resources", "all namespaces"),
                False,
                id="broad-namespaces-prose-is-insufficient",
            ),
            pytest.param(
                ACTIONABILITY_CONCRETE_PROSE_RBAC_PLAN.replace("vector-store resources", "all vector-store resources"),
                False,
                id="broad-named-resource-prose-is-insufficient",
            ),
            pytest.param(
                ACTIONABILITY_CONCRETE_PROSE_RBAC_PLAN,
                True,
                id="concrete-resource-prose-is-accepted",
            ),
            pytest.param(
                ACTIONABILITY_GENERIC_PROSE_RBAC_PLAN.replace("all resources", "the test-namespace namespace"),
                True,
                id="named-namespace-prose-is-accepted",
            ),
        ),
    )
    def test_distinguishes_generic_and_concrete_prose_rbac_evidence(self, tmp_path, plan_content, expected_valid):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(plan_content)

        result = validate_actionability(str(plan))

        assert result["valid"] is expected_valid
        if not expected_valid:
            assert "RBAC roles and permissions" in result["missing_details"]

    @pytest.mark.parametrize(
        "placeholder",
        ("[sample payload]", "<sample payload>", "{sample payload}"),
        ids=("square-brackets", "angle-brackets", "braces"),
    )
    def test_rejects_delimited_placeholder_as_a_test_data_example(self, tmp_path, placeholder):
        plan = tmp_path / "TestPlan.md"
        plan.write_text(ACTIONABILITY_DELIMITED_DATA_PLACEHOLDER_PLAN.format(placeholder=placeholder))

        result = validate_actionability(str(plan))

        assert result["valid"] is False
        assert "test data formats and examples" in result["missing_details"]
