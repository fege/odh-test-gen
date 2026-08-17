"""Gap-consolidation fixtures (GAPS_*) for consolidate_gaps tests."""

GAPS_ENDPOINTS_DUPLICATE = """## Gaps

- **Catalog endpoint request/response schema is undefined** — would be resolved by: API spec
- **Pagination parameters are not specified** — would be resolved by: API spec
"""

GAPS_RISKS_DUPLICATE = """## Gaps

- **The request and response contract for the catalog API is missing** — would be resolved by: API specification
- **KServe CSI configuration details are missing** — would be resolved by: ADR
"""

GAPS_INFRA_SINGLETON = """## Gaps

- **Database failover behavior is not documented** — would be resolved by: design doc
"""

GAPS_ENDPOINTS_UNRECOGNIZED = """## Gaps

- **Load balancer timeout strategy not defined** — would be resolved by: runbook
"""

GAPS_MALFORMED_NO_RESOLVED_BY = """## Gaps

- **Some concern that lacks the resolved-by clause**
"""

GAPS_ALL_EMPTY = """## Gaps

No gaps identified.
"""

GAPS_ENDPOINTS_SYNONYM_NORMALIZATION = """## Gaps

- **The API specification for chat is missing** — would be resolved by: openapi
"""

GAPS_RISKS_SYNONYM_NORMALIZATION = """## Gaps

- **Feature requirements not clear** — would be resolved by: refinement
"""

GAPS_ENDPOINTS_EXACT_DUP = """## Gaps

- **Catalog endpoint request/response schema is undefined** — would be resolved by: API spec
"""

GAPS_RISKS_EXACT_DUP = """## Gaps

- **Catalog endpoint request/response schema is undefined** — would be resolved by: API spec
"""

GAPS_ENDPOINTS_FULL_ANALYZER_DOC = """## Test Tools

- pytest
- playwright

## Gaps

- **Auth flow undefined** — would be resolved by: API spec
"""

GAPS_PREFIX_SIBLING_HEADING = """## Gaps

- **Auth flow undefined** — would be resolved by: API spec

## Gaps extra

- **This must not be parsed as a gap** — would be resolved by: ADR
"""

GAPS_WITH_TRAILING_SECTION = """## Gaps

- **Missing ADR** — would be resolved by: ADR

## Implementation Notes

- More bullets here
- These should NOT be parsed
"""

GAPS_BARE_GAPS_ONLY = """## Gaps

- **X** — would be resolved by: ADR
"""

GAPS_UPPERCASE_HEADING = """## Test Tools

- pytest
- playwright

## GAPS

- **Auth flow undefined** — would be resolved by: API spec
"""

GAPS_LOWERCASE_HEADING = """## Test Tools

- pytest
- playwright

## gaps

- **Auth flow undefined** — would be resolved by: API spec
"""

# Trailing spaces cannot live in the source (pre-commit trailing-whitespace hook).
GAPS_TRAILING_WHITESPACE_HEADING = (
    "## Test Tools\n"
    "\n"
    "- pytest\n"
    "- playwright\n"
    "\n"
    "## Gaps" + "   \n"
    "\n"
    "- **Auth flow undefined** — would be resolved by: API spec\n"
)

GAPS_EMPTY_UPPERCASE_HEADING = """## GAPS

"""

GAPS_NO_HEADING = """- **Some gap** — would be resolved by: ADR
"""

GAPS_WRAPPED_BULLET = """## Gaps

- **Auth token refresh path is undocumented**
  — would be resolved by: ADR
"""

GAPS_WRAPPED_THEN_NORMAL = """## Gaps

- **Auth token refresh path is undocumented**
  — would be resolved by: ADR
- **Another gap** — would be resolved by: API spec
"""

GAPS_DOC_TYPE_PERIOD = """## Gaps

- **Test gap** — would be resolved by: ADR.
"""

GAPS_DOC_TYPE_PERIOD_APISPEC = """## Gaps

- **Test gap for API** — would be resolved by: API spec.
"""

GAPS_PLAIN_HYPHEN_SEPARATOR = """## Gaps

- **Test gap** - would be resolved by: ADR
"""

GAPS_CAPITALIZED_RESOLVED_BY = """## Gaps

- **Test gap** — would be Resolved By: ADR
"""

GAPS_BULLET_THEN_NO_GAPS_LINE = """## Gaps

- **Real gap** — would be resolved by: ADR
No gaps identified.
"""

GAPS_DOC_TYPE_ONLY_PUNCT = """## Gaps

- **X** — would be resolved by: .
"""

GAPS_NEXT_PROCEED = "proceed"
GAPS_NEXT_PROMPT_USER = "prompt_user"
