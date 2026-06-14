# Next Task

`NEXT_TASK.md` is the short-form recommendation output for Level 3 Objective-Driven Planning. It must be derived from `OBJECTIVES.md`, not used as the sole planning source.

## Recommended Level 3 Objective-Driven Task Batch

These tasks are ordered by impact and independence. Pick one unless the user explicitly approves parallel work with disjoint file ownership.

### 1. Outcome-validate `./tes dev --demo-run`

- Objective: One-command local onboarding
- Milestone: Unified local startup / Outcome validation
- Lane: Dev Workflow
- Impact: High. Proves or blocks the first objective's user-visible success path.
- Risk: Medium. Local startup may expose environment, port, or dashboard/API integration issues.
- Dependencies: Existing `./tes dev --demo-run`, local Python/API environment, dashboard runtime, persisted run storage.
- Goal: Prove the already-implemented local development workflow through the observable dashboard/run/replay outcome.
- Suggested file ownership: no product-code ownership for validation-only mode; if a defect is found, scope a follow-up fix to the smallest affected files.
- Avoid touching: engine matching behavior, Python-visible event contracts, dashboard behavior, and strict command/event models unless a defect requires an explicitly scoped follow-up.
- Validation target: run the existing command-level tests that cover the root `tes` launcher if selected, then run `./tes dev --demo-run` and capture the generated `run_id`, dashboard health, run detail, and replay availability.

Success Scenario:
1. `./tes dev --demo-run` starts the persisted API and dashboard.
2. Dashboard health confirms the API is OK.
3. The command prints a non-empty `run_id`.
4. The generated run appears in the dashboard run list or API run listing.
5. The run detail and replay pages load for the printed `run_id`.
6. Shut down cleanly.

### 2. Verify dashboard run and replay visibility

- Objective: One-command local onboarding
- Milestone: Outcome validation
- Lane: Dashboard/UI
- Impact: High. Confirms the user-visible part of onboarding after startup.
- Risk: Medium. May reveal UI, API, or local data gaps that require a separately scoped implementation task.
- Dependencies: Successful local startup and generated demo run ID.
- Goal: Inspect the dashboard run list, run detail, and replay pages using the generated demo run.
- Suggested file ownership: investigation report only unless implementation is explicitly approved.
- Avoid touching: product code during investigation-only mode.
- Validation target: browser or API evidence that the run and replay surfaces load for the generated run.

Success Scenario:
1. Use the demo-run `run_id`.
2. Open or query the run list.
3. Confirm the generated run is visible.
4. Open run detail.
5. Open replay.
6. Record any blocker or missing evidence.

### 3. Define automated onboarding smoke validation

- Objective: One-command local onboarding
- Milestone: Automated smoke validation
- Lane: Tests/Documentation
- Impact: Medium. Converts proven manual outcome evidence into repeatable validation.
- Risk: Low to Medium. Automation before stable manual proof could encode fragile assumptions, so this should follow task 1.
- Dependencies: Current evidence that `./tes dev --demo-run` succeeds and replay visibility is proven or blockers are understood.
- Goal: Scope the smallest automated smoke task that validates startup, health, generated run visibility, replay visibility, and clean shutdown through `./tes`.
- Suggested file ownership: task plan or test files only after explicit implementation approval.
- Avoid touching: matching behavior and command/event contracts.
- Validation target: proposed smoke validation command and success scenario, or implemented smoke test if separately approved.

Success Scenario:
1. Read objective evidence from the completed onboarding validation.
2. Identify the smallest reliable smoke path.
3. Recommend or implement the smoke validation only within approved scope.

## Current Recommendation

Start with task 1: outcome-validate `./tes dev --demo-run`. The command already exists, so the highest-value next step is proving the actual operator workflow and recording current evidence against the One-command local onboarding objective.

## Permissions

- Do not commit without explicit user approval.
- Do not push without explicit user approval.
- Stop after the completion report unless the user asks for the next action.
