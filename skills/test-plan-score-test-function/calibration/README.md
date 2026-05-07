# Test Scorer Calibration Files

## Purpose

These files train the **test-plan.score.test-function** scorer agent to distinguish high-quality tests (9-10/10) from low-quality tests (3-4/10).

**Key distinction:**
- **Tiger Team rules** (`~/Code/Red-Hat-Quality-Tiger-Team/.claude/rules/`) → Train the CODE GENERATOR (how to write tests)
- **Calibration files** (this directory) → Train the SCORER (what quality looks like)

## Hybrid Approach

### Frameworks WITH Tiger Team Rules

For TypeScript, Go, and Cypress, calibration files:
- ✅ Reference Tiger Team rules for patterns (avoid duplication)
- ✅ Focus on demonstrating QUALITY LEVEL (9/10 vs 3/10)
- ✅ Show complete examples with explicit rubric scoring

**Files:**
- `good-go-test.go` / `poor-go-test.go`
- `good-typescript-test.spec.tsx` / `poor-typescript-test.spec.tsx`
- `good-cypress-test.cy.ts` / `poor-cypress-test.cy.ts`

### Frameworks WITHOUT Tiger Team Rules

For pytest (no Tiger Team rules exist yet), calibration files are **standalone**:
- ✅ Complete pattern guidance
- ✅ Quality scoring demonstration

**Files:**
- `good-pytest-test.py` / `poor-pytest-test.py`

## Calibration File Structure

Each file has a header with:

```
// SCORER CALIBRATION: [HIGH|LOW] QUALITY test (should score X/10)
//
// Purpose: Trains scorer to recognize [excellent|poor] [framework] test quality.
//          For PATTERN guidance, see Tiger Team rules at: [path] (if available)
//
// Rubric Scores (5 criteria, 0-2 each, total 10):
// ✅/❌ Coverage: X/2 - [explanation]
// ✅/❌ Assertions: X/2 - [explanation]
// ✅/❌ Conventions: X/2 - [explanation]
// ✅/❌ Test Data: X/2 - [explanation]
// ✅/❌ Code Quality: X/2 - [explanation]
//
// This example demonstrates QUALITY LEVEL (X/10), not just patterns.
```

## Scoring Rubric

### Coverage (0-2 points)
- **2**: All TC requirements implemented (preconditions, steps, assertions)
- **1**: Missing 1-2 items, or has TODOs for specified requirements
- **0**: Missing major sections or mostly TODOs

### Assertions (0-2 points)
- **2**: Specific assertions with clear messages
- **1**: Some generic assertions or missing messages
- **0**: Mostly generic assertions or expected results have TODOs

### Conventions (0-2 points)
- **2**: Follows framework patterns and repo conventions
- **1**: Mostly follows with 1-2 deviations
- **0**: Uses patterns not in conventions, invents markers/helpers

### Test Data (0-2 points)
- **2**: Uses exact values from TC test data
- **1**: Reasonable values but not from TC
- **0**: Placeholders ("test123") or wrong formats

### Code Quality (0-2 points)
- **2**: No TODOs for specified requirements, clean implementation
- **1**: Some TODOs for unclear items, minor issues
- **0**: Many TODOs for TC-specified items, fabricated helpers

## Verdict Mapping

| Score | Verdict | Action |
|-------|---------|--------|
| 9-10  | Ready   | Accept |
| 7-8   | Good    | Accept |
| 4-6   | Revise  | Auto-revision |
| 0-3   | Rework  | Flag for manual review |

## When to Update

**Add new calibration files when:**
- Supporting a new test framework (e.g., Robot Framework, Playwright)
- Tiger Team adds rules for pytest (can then simplify our pytest calibration)

**Update existing files when:**
- Rubric criteria change
- Tiger Team rules significantly evolve
- Quality expectations shift

## Relationship to Tiger Team

**Current state (2026-04-20):**
- Tiger Team has: TypeScript, Go, Cypress rules (pattern guidance)
- Tiger Team missing: pytest rules
- Calibration complements Tiger Team by adding quality scoring

**If Tiger Team adds quality scoring in the future:**
- We can further reduce duplication
- Calibration can become even leaner (just reference Tiger Team scores)
- But scoring will likely remain separate (different purpose)
