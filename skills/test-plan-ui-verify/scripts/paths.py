"""Shared path constants for test-plan.ui-verify scripts.

Defined once here; all scripts import rather than recalculate.
Follows the same pattern as scripts/utils/component_map.py — one source
of truth, imported by whoever needs it.
"""
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent   # .claude/skills/test-plan.ui-verify/
TMP_DIR   = SKILL_DIR / ".tmp"
