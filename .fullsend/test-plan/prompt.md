---
name: test-plan
description: >
  Runs one existing test-plan skill invocation for a single feature in a
  Fullsend target workspace.
---

Read `FULLSEND_TASK` and execute its single top-level skill invocation once.
The host supplies one of these forms:

- `/test-plan-create <JIRA_KEY> --output-dir <relative-path>`
- `/test-plan-create-cases <local-feature-dir>`

Follow the invoked skill's existing instructions, analysis and review workflow,
and normal Jira behavior. Do not discover or batch Jira issues, decide case
eligibility, invoke publishing, or start another top-level task.

For `/test-plan-create`, finish its plan generation and review flow, then stop.
If the skill offers automatic case generation, choose its review-only path. The
trusted host decides eligibility and may start a separate case-generation run.

After the skill finishes, write valid JSON to
`$FULLSEND_OUTPUT_DIR/agent-result.json` with `feature_dir` set to the feature
directory produced or updated by the skill, relative to `FULLSEND_TARGET_REPO_DIR`
(for example, `plans/my_feature`). For `/test-plan-create` only, if Step 1.5
stopped because the strategy has no acceptance criteria and wrote the score-zero
review, also set `no_acceptance_criteria` to `true`. Omit that field otherwise.
The host uses the result to retrieve the plan, review, handoff files, and any
test cases from the validated sandbox workspace. Do not write a result for an
incomplete or failed skill invocation.
