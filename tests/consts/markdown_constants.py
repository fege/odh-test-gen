"""Markdown fixtures for extract_section tests."""

EXTRACT_GAPS_WITH_PREFIX_SIBLING = """preamble
## Gaps
- gap 1
### Details
- gap 2
## Gaps extra
- not a gap
## Other
- unrelated
"""

EXTRACT_GAPS_DUPLICATE_HEADING = """## Gaps
- first
## Gaps
- second
## Other
- unrelated
"""

EXTRACT_GAPS_EMPTY_THEN_OTHER = """## Gaps
## Other
- unrelated
"""

EXTRACT_GAPS_LEVEL_ONE_BETWEEN = """## Gaps
- gap
# Other
- text
## Final
- final
"""

# Trailing spaces cannot live at the end of a source line (pre-commit hook).
EXTRACT_GAPS_TRAILING_WS_HEADING = "## Gaps" + "   \n" + "- gap\n## Other\n- unrelated\n"

EXTRACT_GAPS_MISSING = """## Other
- x
"""

EXTRACT_HEADING_HASH_IN_TITLE = """## C#
- gap
### Details
- child
# Other
- done
"""
