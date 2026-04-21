"""
Schema definitions and validation for test plan artifacts.

Defines schemas for:
- test-plan (TestPlan.md)
- test-case (TC-*.md)
- test-gaps (TestPlanGaps.md)
- test-plan-review (TestPlanReview.md)

Provides validation and default value application.
"""

import os
import re
import sys

try:
    import yaml
except ImportError:
    print(
        "Error: PyYAML is required but not installed.\n"
        "Install it with: uv pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


# ─── Schema Definitions ────────────────────────────────────────────────────────

# Each schema is a dict of field_name -> field_spec.
# field_spec keys:
#   type:     "string" | "int" | "bool" | "list" | "dict"
#   required: bool (default False)
#   enum:     list of allowed values (optional)
#   pattern:  regex pattern the value must match (optional, strings only)
#   default:  default value when not provided (optional)
#   fields:   sub-field specs (required for type "dict")

SCHEMAS = {
    "test-plan": {
        "feature": {
            "type": "string",
            "required": True,
        },
        "source_key": {
            "type": "string",
            "required": True,
            "pattern": r"^(RHAISTRAT|RHOAIENG)-\d+$",
        },
        "source_type": {
            "type": "string",
            "required": False,
            "enum": ["strat", "issue"],
            "default": None,
        },
        "version": {
            "type": "string",
            "required": True,
            "pattern": r"^\d+\.\d+\.\d+$",
        },
        "status": {
            "type": "string",
            "required": True,
            "enum": ["Draft", "In Review", "Approved"],
        },
        "last_updated": {
            "type": "string",
            "required": True,
        },
        "author": {
            "type": "string",
            "required": True,
        },
        "additional_docs": {
            "type": "list",
            "required": False,
            "default": [],
        },
        "reviewers": {
            "type": "list",
            "required": False,
            "default": [],
        },
    },
    "test-case": {
        "test_case_id": {
            "type": "string",
            "required": True,
            "pattern": r"^TC-[A-Z0-9]+-\d+$",
        },
        "source_key": {
            "type": "string",
            "required": True,
            "pattern": r"^(RHAISTRAT|RHOAIENG)-\d+$",
        },
        "priority": {
            "type": "string",
            "required": True,
            "enum": ["P0", "P1", "P2"],
        },
        "status": {
            "type": "string",
            "required": True,
            "enum": ["Draft", "Ready", "Automated", "Blocked"],
        },
        "automation_status": {
            "type": "string",
            "required": False,
            "enum": ["Not Started", "In Progress", "Complete", "N/A"],
            "default": "Not Started",
        },
        "automation_file": {
            "type": "string",
            "required": False,
            "default": None,
        },
        "automation_function": {
            "type": "string",
            "required": False,
            "default": None,
        },
        "last_updated": {
            "type": "string",
            "required": True,
        },
    },
    "test-gaps": {
        "feature": {
            "type": "string",
            "required": True,
        },
        "source_key": {
            "type": "string",
            "required": True,
            "pattern": r"^(RHAISTRAT|RHOAIENG)-\d+$",
        },
        "status": {
            "type": "string",
            "required": True,
            "enum": ["Open", "Partially Resolved", "Resolved"],
        },
        "gap_count": {
            "type": "int",
            "required": True,
        },
        "last_updated": {
            "type": "string",
            "required": True,
        },
    },
    "test-plan-review": {
        "feature": {
            "type": "string",
            "required": True,
        },
        "source_key": {
            "type": "string",
            "required": True,
            "pattern": r"^(RHAISTRAT|RHOAIENG)-\d+$",
        },
        "score": {
            "type": "int",
            "required": True,
            "min": 0,
            "max": 10,
        },
        "pass": {
            "type": "bool",
            "required": True,
        },
        "verdict": {
            "type": "string",
            "required": True,
            "enum": ["Ready", "Revise", "Rework"],
        },
        "scores": {
            "type": "dict",
            "required": True,
            "fields": {
                "specificity": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
                "grounding": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
                "scope_fidelity": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
                "actionability": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
                "consistency": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
            },
        },
        "auto_revised": {
            "type": "bool",
            "required": True,
            "default": False,
        },
        "before_score": {
            "type": "int",
            "required": False,
            "default": None,
            "min": 0,
            "max": 10,
        },
        "before_scores": {
            "type": "dict",
            "required": False,
            "default": None,
            "fields": {
                "specificity": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
                "grounding": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
                "scope_fidelity": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
                "actionability": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
                "consistency": {
                    "type": "int",
                    "required": True,
                    "min": 0,
                    "max": 2,
                },
            },
        },
        "error": {
            "type": "string",
            "required": False,
            "default": None,
        },
        "last_updated": {
            "type": "string",
            "required": True,
        },
    },
}


# ─── Auto-detection ─────────────────────────────────────────────────────────────

def detect_schema_type(path):
    """Detect schema type from file path."""
    basename = os.path.basename(path)
    if basename == "TestPlanGaps.md":
        return "test-gaps"
    if basename == "TestPlanReview.md":
        return "test-plan-review"
    if basename.startswith("TC-"):
        return "test-case"
    if basename == "TestPlan.md":
        return "test-plan"
    return None


# ─── Validation ─────────────────────────────────────────────────────────────────

class ValidationError(Exception):
    """Raised when frontmatter fails schema validation."""
    pass


def _validate_field(name, value, spec):
    """Validate a single field against its spec. Returns list of errors."""
    errors = []

    if value is None:
        if spec.get("required", False) and "default" not in spec:
            errors.append(f"Missing required field: {name}")
        return errors

    expected_type = spec.get("type", "string")

    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(
                f"{name}: expected string, got {type(value).__name__}")
            return errors
        if "enum" in spec and value not in spec["enum"]:
            errors.append(
                f"{name}: '{value}' not in {spec['enum']}")
        if "pattern" in spec and not re.match(spec["pattern"], value):
            errors.append(
                f"{name}: '{value}' does not match {spec['pattern']}")

    elif expected_type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(
                f"{name}: expected int, got {type(value).__name__}")
        else:
            if "min" in spec and value < spec["min"]:
                errors.append(
                    f"{name}: {value} is less than minimum {spec['min']}")
            if "max" in spec and value > spec["max"]:
                errors.append(
                    f"{name}: {value} is greater than maximum {spec['max']}")

    elif expected_type == "bool":
        if not isinstance(value, bool):
            errors.append(
                f"{name}: expected bool, got {type(value).__name__}")

    elif expected_type == "list":
        if not isinstance(value, list):
            errors.append(
                f"{name}: expected list, got {type(value).__name__}")

    elif expected_type == "dict":
        if not isinstance(value, dict):
            errors.append(
                f"{name}: expected dict, got {type(value).__name__}")
        elif "fields" in spec:
            for sub_name, sub_spec in spec["fields"].items():
                errors.extend(_validate_field(
                    f"{name}.{sub_name}", value.get(sub_name), sub_spec))
            for sub_key in value:
                if sub_key not in spec["fields"]:
                    errors.append(f"{name}: unknown sub-field '{sub_key}'")

    return errors


def validate(data, schema_type):
    """Validate frontmatter data against a schema.

    Args:
        data: dict of frontmatter fields
        schema_type: one of the keys in SCHEMAS

    Returns:
        list of error strings (empty if valid)

    Raises:
        ValueError: if schema_type is unknown
    """
    if schema_type not in SCHEMAS:
        raise ValueError(
            f"Unknown schema type: {schema_type}. "
            f"Valid types: {list(SCHEMAS.keys())}")

    schema = SCHEMAS[schema_type]
    errors = []

    for key in data:
        if key not in schema:
            errors.append(f"Unknown field: {key}")

    for field_name, field_spec in schema.items():
        errors.extend(_validate_field(
            field_name, data.get(field_name), field_spec))

    if schema_type == "test-plan-review":
        criteria = (
            "specificity",
            "grounding",
            "scope_fidelity",
            "actionability",
            "consistency",
        )
        scores = data.get("scores")
        score = data.get("score")
        if isinstance(scores, dict) and isinstance(score, int):
            if all(isinstance(scores.get(k), int) for k in criteria):
                expected = sum(scores[k] for k in criteria)
                if score != expected:
                    errors.append(
                        f"score: expected {expected} from scores.*, got {score}"
                    )

        before_scores = data.get("before_scores")
        before_score = data.get("before_score")
        if (before_score is None) != (before_scores is None):
            errors.append(
                "before_score and before_scores must both be set or both be null"
            )
        if isinstance(before_scores, dict) and isinstance(before_score, int):
            if all(isinstance(before_scores.get(k), int) for k in criteria):
                expected_before = sum(before_scores[k] for k in criteria)
                if before_score != expected_before:
                    errors.append(
                        "before_score: expected "
                        f"{expected_before} from before_scores.*, got {before_score}"
                    )

    return errors


def apply_defaults(data, schema_type):
    """Apply default values for missing optional fields.

    Modifies data in-place and returns it.
    """
    schema = SCHEMAS[schema_type]
    for field_name, field_spec in schema.items():
        if field_name not in data and "default" in field_spec:
            data[field_name] = field_spec["default"]
    return data


def get_schema_yaml(schema_type):
    """Return the schema definition as a YAML string for display."""
    if schema_type not in SCHEMAS:
        raise ValueError(
            f"Unknown schema type: {schema_type}. "
            f"Valid types: {list(SCHEMAS.keys())}")

    schema = SCHEMAS[schema_type]
    output = {"required": {}, "optional": {}}

    for name, spec in schema.items():
        entry = {"type": spec["type"]}
        if "enum" in spec:
            entry["enum"] = spec["enum"]
        if "pattern" in spec:
            entry["pattern"] = spec["pattern"]
        if "default" in spec:
            entry["default"] = spec["default"]
        if "min" in spec:
            entry["min"] = spec["min"]
        if "max" in spec:
            entry["max"] = spec["max"]
        if "fields" in spec:
            entry["fields"] = {
                k: {
                    "type": v["type"],
                    **({"min": v["min"]} if "min" in v else {}),
                    **({"max": v["max"]} if "max" in v else {}),
                }
                for k, v in spec["fields"].items()
            }

        if spec.get("required", False):
            output["required"][name] = entry
        else:
            output["optional"][name] = entry

    return yaml.dump(output, default_flow_style=False, sort_keys=False)


