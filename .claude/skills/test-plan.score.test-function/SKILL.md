---
name: test-plan.score.test-function
description: Score generated test function code for completeness, quality, and convention adherence using a 5-criteria rubric
context: fork
allowed-tools: Read
model: opus
user-invocable: false
---

# Test Function Quality Scorer

Internal scorer sub-agent that evaluates generated test function code using a 5-criteria quality rubric. Forked by `test-plan.case-implement` in Step 5.6.

## Usage

This skill is not user-invocable. It is called by:
- `test-plan.case-implement` (Step 5.6) for quality assurance of generated tests

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract:
1. **`--test-code-file`**: Path to file containing generated test code
2. **`--tc-file`**: Path to TC-*.md specification
3. **`--conventions-file`**: Path to repository conventions markdown
4. **`--framework`**: Test framework (pytest, Go testing, Jest, etc.)

## Process

### Step 1: Read Scoring Instructions

Read the detailed scoring rubric from `${CLAUDE_SKILL_DIR}/prompts/score-test-function.md`.

### Step 2: Execute Scoring

Apply the prompt with substitutions:
- `{TEST_CODE_FILE}` = `--test-code-file` argument
- `{TC_FILE}` = `--tc-file` argument
- `{CONVENTIONS_FILE}` = `--conventions-file` argument
- `{FRAMEWORK}` = `--framework` argument

The scoring rubric evaluates:
1. **Coverage** (0-2): All TC requirements implemented?
2. **Assertions** (0-2): Specific and meaningful?
3. **Convention Adherence** (0-2): Follows repo patterns?
4. **Test Data** (0-2): Uses realistic values from TC?
5. **Code Quality** (0-2): Clean, no excessive TODOs?

### Step 3: Return Assessment

Return the structured markdown assessment from the scorer.

The output includes:
- Per-criterion scores with issues
- Total score (0-10)
- Verdict (Ready/Good/Revise/Rework)
- Coverage analysis (preconditions, steps, assertions implemented)
- Specific issues found
- Revision recommendations (if needed)

## What This Skill Does NOT Do

- Does NOT write score to a file
- Does NOT modify the generated test code
- Does NOT trigger auto-revision (that's handled by the orchestrating skill)
- For scoring + auto-revision, the orchestrating skill (`test-plan.case-implement`) handles the revision loop

$ARGUMENTS
