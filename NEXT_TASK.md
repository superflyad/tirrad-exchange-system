# Next Task

## Recommended First Level 3 Task Batch

These tasks are ordered by impact and independence. Pick one unless the user explicitly approves parallel work with disjoint file ownership.

### 1. Implement `./tes dev --demo-run`

- Lane: Dev Workflow
- Goal: Create a deterministic demo-run workflow that proves the Level 3 operating loop through an observable local outcome.
- Suggested file ownership: `tes`, workflow documentation for the command, and focused tests for the command behavior.
- Avoid touching: engine matching behavior, Python-visible event contracts, dashboard behavior, and strict command/event models unless explicitly approved.
- Validation target: Run the command-level tests added for the workflow, then run broader `./tes` validation that matches the final implementation scope.

Success Scenario:
1. Start the local stack or required local surfaces.
2. Open or verify the dashboard health surface.
3. Generate a deterministic demo run.
4. Verify the run appears in the expected run listing or output.
5. Verify replay data loads or is available through the expected path.
6. Shut down cleanly.

### 2. Document Level 3 contributor usage

- Lane: Tests/Documentation
- Goal: Add contributor-facing guidance for using the Level 3 intake, state update, and completion report loop after the first operating-loop task proves the workflow.
- Suggested file ownership: documentation files only.
- Avoid touching: product code and workflow command behavior.
- Validation target: `git status`, `git diff --stat`, `git diff --check`, plus any docs checks that exist at the time.

Success Scenario:
1. A contributor can identify which state files Codex reads before work.
2. A contributor can identify which state files Codex updates after work.
3. A contributor can copy a valid Level 3 task prompt and completion report structure.

### 3. Inspect dashboard run/replay validation gaps

- Lane: Dashboard/UI
- Goal: Identify the smallest independent dashboard workflow validation gap to implement after `./tes dev --demo-run` exists.
- Suggested file ownership: investigation report only unless implementation is explicitly approved.
- Avoid touching: product code during investigation-only mode.
- Validation target: report-only success scenario unless a follow-up implementation task is approved.

Success Scenario:
1. Read dashboard run, replay, and live monitor surfaces.
2. Identify current tests or missing tests for the run/replay workflow.
3. Recommend one scoped UI validation task with non-overlapping file ownership.

## Current Recommendation

Start with task 1: implement `./tes dev --demo-run`. It has the highest operating-loop value because it turns the workflow standard into an executable local path.

## Permissions

- Do not commit without explicit user approval.
- Do not push without explicit user approval.
- Stop after the completion report unless the user asks for the next action.
