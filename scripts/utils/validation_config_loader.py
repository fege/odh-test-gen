"""Config loader for validation pattern files.

Loads core patterns from ``scripts/checks/core/`` and, optionally, additional team-specific
patterns from ``scripts/checks/<team>/``.
Team configs extend core configs additively — patterns are unioned, never removed or overridden,
and the merged result is deduplicated so a pattern present in both core and a team config isn't checked twice.

A missing team folder/file is not an error (teams are opt-in and may not have customized a
given check yet): it's logged as a warning and loading continues with core-only patterns.
An invalid (unparseable) JSON file *is* an error.
"""

import json
import logging
from collections.abc import Mapping
from pathlib import Path

logger = logging.getLogger(__name__)

# TestPlan.md section number -> boilerplate pattern category (see boilerplate_patterns.json
# schema)
BOILERPLATE_SECTION_CATEGORIES = {
    "1.3": "objectives",
    "2.3": "priorities",
    "8": "risks",
}
_BOILERPLATE_CATEGORIES = tuple(dict.fromkeys(BOILERPLATE_SECTION_CATEGORIES.values()))


def _load_json(path: Path) -> dict:
    """Read and parse a JSON config file, raising a clear error on malformed content."""
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in validation config file {path}: {exc}") from exc


def parse_teams_arg(include_teams: str) -> list[str] | None:
    """Parse a CLI ``--include-teams=a,b,c`` value into a list, or None if empty.

    Shared by validate_test_scope.py and detect_boilerplate.py, whose --include-teams flags
    both feed straight into load_scope_patterns/load_boilerplate_patterns.
    """
    teams = [t.strip() for t in include_teams.split(",") if t.strip()]
    return teams or None


def _dedupe(items: list) -> list:
    """Return items in first-seen order with duplicates removed."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _require_list_str(value, field: str) -> None:
    """Raise ValueError unless value is a list of strings (rejects str, None, nested lists)."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")


def _require_mapping(value, field: str) -> None:
    """Raise ValueError unless value is a mapping."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")


def _list_str_field(config: dict, field: str) -> list[str]:
    """Return config[field] as list[str], defaulting to [] when the key is absent."""
    _require_mapping(config, "validation config")
    value = config.get(field, [])
    _require_list_str(value, field)
    return list(value)


def _boilerplate_category_lists(config: dict) -> dict[str, list[str]]:
    """Return objectives/risks/priorities lists from config['patterns'], validating types."""
    _require_mapping(config, "validation config")
    patterns = config.get("patterns", {})
    _require_mapping(patterns, "patterns")
    categories: dict[str, list[str]] = {}
    for category in _BOILERPLATE_CATEGORIES:
        value = patterns.get(category, [])
        _require_list_str(value, category)
        categories[category] = list(value)
    return categories


def _iter_team_configs(checks_dir: Path, teams: list[str] | None, filename: str):
    """Yield parsed team config dicts, skipping (with a warning) any team missing the file."""
    for team in teams or []:
        team_path = checks_dir / team / filename
        if not team_path.exists():
            logger.warning(
                "Validation config for team '%s' not found at %s; skipping team patterns for this check.",
                team,
                team_path,
            )
            continue
        yield _load_json(team_path)


def load_scope_patterns(checks_dir: str = "scripts/checks", teams: list[str] | None = None) -> dict:
    """Load scope validation patterns from core and team-specific configs.

    Args:
        checks_dir: Base directory for check config files
        teams: List of team names to load patterns from (additive merge with core)

    Returns:
        Merged pattern config dict with keys: version, allowed_test_levels,
        forbidden_test_levels, forbidden_patterns.

    Raises:
        FileNotFoundError: if the core config file is missing
        ValueError: if a config file contains invalid JSON or non-list[str] list fields
    """
    checks_path = Path(checks_dir)
    core = _load_json(checks_path / "core" / "scope_patterns.json")

    allowed_test_levels = _list_str_field(core, "allowed_test_levels")
    forbidden_test_levels = _list_str_field(core, "forbidden_test_levels")
    forbidden_patterns = _list_str_field(core, "forbidden_patterns")

    for team_config in _iter_team_configs(checks_path, teams, "scope_patterns.json"):
        allowed_test_levels.extend(_list_str_field(team_config, "allowed_test_levels"))
        forbidden_test_levels.extend(_list_str_field(team_config, "forbidden_test_levels"))
        forbidden_patterns.extend(_list_str_field(team_config, "forbidden_patterns"))

    return {
        "version": core.get("version", "1.0"),
        "allowed_test_levels": _dedupe(allowed_test_levels),
        "forbidden_test_levels": _dedupe(forbidden_test_levels),
        "forbidden_patterns": _dedupe(forbidden_patterns),
    }


def load_boilerplate_patterns(checks_dir: str = "scripts/checks", teams: list[str] | None = None) -> dict:
    """Load boilerplate detection patterns from core and team-specific configs.

    Args:
        checks_dir: Base directory for check config files
        teams: List of team names to load patterns from (additive merge with core)

    Returns:
        Merged pattern config dict with keys: version, patterns (dict of
        objectives/risks/priorities lists).

    Raises:
        FileNotFoundError: if the core config file is missing
        ValueError: if a config file contains invalid JSON, a non-mapping patterns object,
            or a non-list[str] pattern category
    """
    checks_path = Path(checks_dir)
    core = _load_json(checks_path / "core" / "boilerplate_patterns.json")
    patterns = _boilerplate_category_lists(core)

    for team_config in _iter_team_configs(checks_path, teams, "boilerplate_patterns.json"):
        team_patterns = _boilerplate_category_lists(team_config)
        for category in _BOILERPLATE_CATEGORIES:
            patterns[category].extend(team_patterns[category])

    return {
        "version": core.get("version", "1.0"),
        "patterns": {category: _dedupe(items) for category, items in patterns.items()},
    }
