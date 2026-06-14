# Next Task

## Recommended Level 3 Task Batch

These tasks are ordered by impact and independence. Pick one unless the user explicitly approves parallel work with disjoint file ownership.

### 1. Outcome-validate `./tes dev --demo-run`

- Lane: Dev Workflow
- Goal: Prove the already-implemented local development workflow through the observable dashboard/run/replay outcome.
- Suggested file ownership: no product-code ownership for validation-only mode; if a defect is found, scope a follow-up fix to the smallest affected files.
- Avoid touching: engine matching behavior, Python-visible event contracts, dashboard behavior, and strict command/event models unless a defect requires an explicitly scoped follow-up.
- Validation target: run the existing command-level tests that cover the root `tes` launcher, then run `./tes dev --demo-run` and capture the generated `run_id`, dashboard health, run detail, and replay availability.

Success Scenario:
1. `./tes dev --demo-run` starts the persisted API and dashboard.
2. Dashboard health confirms the API is OK.
3. The command prints a non-empty `run_id`.
4. The generated run appears in the dashboard run list or API run listing.
5. The run detail and replay pages load for the printed `run_id`.
6. Shut down cleanly.

### 2. Document Level 3 contributor usage

- Lane: Tests/Documentation
- Goal: Add contributor-facing guidance for using the Level 3 intake, state update, and completion report loop after the executable workflow has current outcome evidence.
- Suggested file ownership: documentation files only.
- Avoid touching: product code and workflow command behavior.
- Validation target: `git status`, `git diff --stat`, `git diff --check`, plus any docs checks that exist at the time.

Success Scenario:
1. A contributor can identify which state files Codex reads before work.
2. A contributor can identify which state files Codex updates after work.
3. A contributor can copy a valid Level 3 task prompt and completion report structure.

### 3. Inspect dashboard run/replay validation gaps

- Lane: Dashboard/UI
- Goal: Identify the smallest independent dashboard workflow validation gap after the existing `./tes dev --demo-run` path is outcome-validated.
- Suggested file ownership: investigation report only unless implementation is explicitly approved.
- Avoid touching: product code during investigation-only mode.
- Validation target: report-only success scenario unless a follow-up implementation task is approved.

Success Scenario:
1. Read dashboard run, replay, and live monitor surfaces.
2. Identify current tests or missing tests for the run/replay workflow.
3. Recommend one scoped UI validation task with non-overlapping file ownership.

## Current Recommendation

Start with task 1: outcome-validate `./tes dev --demo-run`. The command already exists, so the highest-value next step is proving the actual operator workflow and recording current evidence instead of re-implementing completed work.

## Permissions

- Do not commit without explicit user approval.
- Do not push without explicit user approval.
- Stop after the completion report unless the user asks for the next action.
