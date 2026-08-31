#!/usr/bin/env python3
"""Build the quality gate's inputs, shared by test-plan-review and test-plan-score: derive
ac_count/nfr_categories from a resolved strategy file and run deterministic citation, coverage,
scope-evidence, and actionability validators against TestPlan.md.

Usage:
    uv run python scripts/build_citation_inputs.py <feature_dir> --strategy-file <path>

Exit 0 with status "ok" JSON when gate-input construction and validation ran (including an
ordinary, well-formed validator "invalid" result). Exit 1 with status "error" JSON when
gate-input construction itself failed — the caller must stop, not treat this as data about the
test plan.
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.utils.snapshot_io import read_file_nofollow, require_feature_snapshot
from scripts.utils.strat_utils import gate_inputs
from scripts.validate_quality_evidence import validate_actionability, validate_scope_coverage
from scripts.validate import validate_ac_citations, validate_ac_coverage, validate_interface_coverage


def build_citation_inputs(feature_dir: str, strategy_file: str) -> dict:
    testplan_path = str(Path(feature_dir) / "TestPlan.md")
    interface_coverage_result = validate_interface_coverage(testplan_path)

    safe_path = require_feature_snapshot(feature_dir, strategy_file)
    strategy_content = read_file_nofollow(safe_path)
    inputs = gate_inputs(strategy_content)
    ac_count = inputs["ac_count"]
    nfr_categories = inputs["nfr_categories"]

    return {
        "status": "ok",
        "interface_coverage_result": interface_coverage_result,
        "ac_citations_result": validate_ac_citations(testplan_path, ac_count=ac_count, nfr_categories=nfr_categories),
        "ac_coverage_result": validate_ac_coverage(testplan_path, ac_count=ac_count),
        "scope_coverage_result": validate_scope_coverage(testplan_path, strategy_content),
        "actionability_result": validate_actionability(testplan_path),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature_dir")
    parser.add_argument("--strategy-file", required=True, help="Path to the resolved strategy file")
    args = parser.parse_args()

    try:
        result = build_citation_inputs(args.feature_dir, args.strategy_file)
    except Exception:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": "citation_input_construction_failed",
                },
                indent=2,
            )
        )
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
