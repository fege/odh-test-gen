---
name: test-plan.analyze.placement
description: Analyze test cases and recommend placement (component repo vs downstream E2E repo)
context: fork
allowed-tools: Read, AskUserQuestion
model: opus
user-invocable: false
---

# Test Case Placement Analyzer

Analyzes test case specifications and recommends whether each should be placed in the component repository (upstream) or downstream E2E repository, based on test level, infrastructure requirements, priority, and repository readiness.

## Usage

This skill is not user-invocable. It is called by:
- `test-plan.case-implement` (Step 2)

## Inputs

### From arguments
Parse `$ARGUMENTS` to extract file paths:
- **`--feature-dir`**: Path to feature directory containing TestPlan.md and test_cases/
- **`--code-repo`**: GitHub repository name (e.g., `opendatahub-io/odh-dashboard`)
- **`--code-repo-readiness`**: Agent readiness level (high, medium, low, none, unknown)
- **`--code-repo-has-tests`**: Boolean (true/false)
- **`--downstream-readiness`**: Downstream repo readiness (high, medium, low)

## Process

### Step 1: Read Test Cases

1. Read `<feature_dir>/TestPlan.md` to understand:
   - Section 4 (Endpoints/Methods Under Test)
   - Section 2 (Test Strategy - levels, types, priorities)
   - Section 1.2 (Scope boundaries)

2. Read all TC-*.md files from `<feature_dir>/test_cases/`:
   - Parse frontmatter: test_case_id, priority, category
   - Extract from body: preconditions, test_steps, expected_results

### Step 2: Placement Philosophy

**Key Principles (refined to address common concerns):**
- **Kubernetes API ≠ Downstream**: Tests using K8s APIs (CRDs, kubectl) can run upstream with envtest/kind
- **P0 ≠ Downstream Only**: P0 unit/integration tests should be upstream for fast feedback (block PRs early)
- **Test level + Infrastructure**: Placement considers BOTH test level (unit/integration/e2e) AND infrastructure (K8s API vs full stack)
- **Fast Feedback Principle**: Critical tests close to code (upstream), comprehensive tests far from code (downstream)

### Step 3: Analyze Each TC for Placement

For each TC:

1. **Extract characteristics** by analyzing TC text (preconditions + steps + expected results):
   
   **Test level signals:**
   - `is_unit`: contains "single function", "isolated", "mock", "unit test", "no dependencies"
   - `is_integration`: contains "multiple components", "database", "service", "integration"
   - `is_api`: contains "HTTP", "REST", "API", "endpoint", "/api/"
   - `is_e2e`: contains "end-to-end", "E2E", "user workflow", "full flow", "UI", "browser"
   - `is_contract`: contains "contract test", "API contract", "schema validation"
   
   **Infrastructure requirement signals:**
   - `requires_k8s_api`: contains "Kubernetes", "K8s", "CRD", "Custom Resource", "kubectl", "namespace" (but NOT "full deployment")
   - `requires_cluster`: contains "OpenShift", "cluster", "pod", "deployment" (actual cluster, not just K8s API)
   - `requires_full_stack`: contains "RHOAI", "ODH", "full deployment", "multiple services", "end-to-end deployment"

2. **Classify test level:**
   - If `is_e2e` AND `requires_full_stack` → level = `e2e`
   - Else if `is_unit` → level = `unit`
   - Else if `is_contract` OR `is_api` → level = `api`
   - Else if `is_integration` → level = `integration`
   - Else if `requires_k8s_api` AND NOT `requires_full_stack` → level = `k8s-integration`
   - Else → level = `component`

3. **Score placement options** (`same_repo`, `downstream`, `both`):

   Initialize scores: `same_repo = 0`, `downstream = 0`, `both = 0`

   **Factor 1: Test level preferences**
   - If level == `unit`:
     - If `code_repo_has_tests`: `same_repo += 10`
     - Else: `downstream += 5`
   - If level == `e2e`:
     - `downstream += 10`
   - If level == `api`:
     - If `code_repo_has_tests`: `both += 8`
     - Else: `downstream += 7`
   - If level == `integration`:
     - If `code_repo_readiness == 'high'` AND `code_repo_has_tests`: `same_repo += 7`
     - Else: `downstream += 8`
   - If level == `k8s-integration`:
     - If `code_repo_has_tests`: `same_repo += 8`
     - Else: `downstream += 6`
   - If level == `component`:
     - If `code_repo_has_tests`: `same_repo += 8`
     - Else: `downstream += 6`

   **Factor 2: Infrastructure requirements**
   - If `requires_full_stack`:
     - `downstream += 10`
     - `same_repo = max(0, same_repo - 5)`
   - Else if `requires_cluster` AND level == `e2e`:
     - `downstream += 7`
   - Else if `requires_k8s_api` AND level in [`unit`, `integration`, `k8s-integration`]:
     - If `code_repo_has_tests`: `same_repo += 5`
     - Else: `downstream += 4`

   **Factor 3: TC priority (P0 strongly prefers upstream for fast feedback)**
   - If `priority == 'P0'`:
     - If level != `e2e`:
       - `same_repo += 10`
       - If level == `api`: `both += 5`
     - Else (level == `e2e`):
       - `downstream += 10`
       - `same_repo = max(0, same_repo - 3)`

   **Factor 4: Code repo agent readiness**
   - If `code_repo_readiness == 'high'`: `same_repo += 3`
   - Else if `code_repo_readiness in ['low', 'none']`: `downstream += 4`

4. **Determine recommended placement:**
   - `recommended_placement` = option with highest score

5. **Store decision** for this TC:
   - `tc['level'] = level`
   - `tc['placement_recommendation'] = recommended_placement`
   - `tc['placement_scores'] = {same_repo: X, downstream: Y, both: Z}`
   - `tc['placement_reasons'] = [list of reasons from scoring]`

### Step 4: Present Decisions and Get User Confirmation

Display placement summary:

```
==========================================
Placement Recommendations for <feature_name>
==========================================

TC-MIG-001 (k8s-integration, P0)
  Characteristics: requires_k8s_api
  Scores: same_repo=28, downstream=0, both=0
  → Recommended: same_repo
  → Reasons: P0 → upstream (fast feedback), K8s integration → envtest

TC-E2E-001 (e2e, P0)
  Characteristics: is_e2e, requires_full_stack
  Scores: same_repo=0, downstream=30, both=0
  → Recommended: downstream
  → Reasons: E2E + full stack → downstream only

Summary:
- same_repo: 5 TCs
- downstream: 2 TCs
- both: 1 TC
==========================================
```

Ask user via AskUserQuestion:

**Question:** "Review placement recommendations?"

**Options:**
1. **Accept all recommendations** (proceed with suggested placements)
2. **Review each TC individually** (approve or override per TC)

If user chooses **Option 1**: Return all decisions as-is.

If user chooses **Option 2**: For each TC, ask:
```
TC-{id} ({level}, {priority})

Recommended: {placement}
Scores: same_repo={X}, downstream={Y}, both={Z}
Reasons: {reasons}

Choose placement:
1. Accept recommendation ({placement})
2. Override to: same_repo
3. Override to: downstream
4. Override to: both
```

For any overrides, update `tc['placement_recommendation']` and add `tc['placement_override'] = True`.

### Step 5: Return Placement Decisions

Return structured output with placement decisions for all TCs:

```json
{
  "tc_placements": [
    {
      "tc_id": "TC-MIG-001",
      "level": "k8s-integration",
      "placement": "same_repo",
      "scores": {"same_repo": 28, "downstream": 0, "both": 0},
      "reasons": ["P0 → upstream (fast feedback)", "K8s integration → envtest"],
      "override": false
    },
    ...
  ]
}
```

## What This Skill Does NOT Do

- Does NOT generate test code (that's test-plan.create.test-function)
- Does NOT write files (just analyzes and returns decisions)
- Does NOT clone repositories (receives repo info as input)

$ARGUMENTS
