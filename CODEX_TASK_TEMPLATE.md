# Codex Task Template

Use this template for Codex tasks. Level 3 Project Operating Loop is active for future work: tasks are complete only when the requested user workflow succeeds or a documented blocker prevents completion, and project state is refreshed afterward.

```markdown
Task:

Objective:

Workflow level:
- Level 3: project operating loop

Mode:
- Investigation-only / Edit

Required pre-task state intake:
- [ ] Read `ROADMAP.md`
- [ ] Read `NEXT_TASK.md`
- [ ] Read `ACTIVE_TASKS.md`
- [ ] Read `COMPLETED_TASKS.md`
- [ ] Read `CODEX_STATE.md`

Work lane:
- Core/API / Dashboard/UI / Dev Workflow / Tests/Documentation

Allowed files:
-

Do not edit:
- Product code unless explicitly listed in allowed files.
- Files outside the approved scope.
- Matching behavior unless explicitly approved.

File ownership:
-

Constraints:
-

Requirements:
-

Contract safety:
- Keep Python-visible event shape exactly `{ "type": "...", "data": {...} }`.
- Do not leak raw C++ internals into Python-visible output.
- Do not expose enum integers, variant indexes, C++ class names, namespaces, debug fields, or implementation-only fields in public Python output.
- Do not weaken parsers or validators.
- Do not pass raw dictionaries beyond parser or serialization boundaries when strict models exist.

Validation Commands:
- [ ] `./tes check`
- [ ] `./tes check python`
- [ ] `./tes check python-release`
- [ ] `cd web && npm run build`
- [ ] `git status`
- [ ] `git diff --stat`
- [ ] `git diff --check`
- [ ] Other:

Success Scenario:
1.
2.
3.

Required post-task state updates:
- [ ] Update `ACTIVE_TASKS.md`
- [ ] Update `COMPLETED_TASKS.md`
- [ ] Update `NEXT_TASK.md`
- [ ] Update `CODEX_STATE.md`

Task recommendation rules:
- Recommend 1-3 next tasks.
- Prefer highest-impact tasks.
- Prefer independent tasks.
- Avoid overlapping file ownership.
- Include lane and validation target for each recommendation.

Acceptance:
-

Permissions:
- Do not commit.
- Do not push.
- Stop after completion report.

Completion report must include:
- Completed task.
- Success scenario result.
- Files changed.
- Validation results.
- State updates.
- Recommended next tasks.

Completion Report:

## Summary
-

## Files Changed
-

## Validation
- `git status`: passed / failed / not run
- `git diff --stat`: passed / failed / not run
- `git diff --check`: passed / failed / not run
- Other commands actually run:

## LEVEL 3 COMPLETION REPORT
Completed task:

Success scenario result:

Files changed:

Validation results:

State updates:

Recommended next tasks:

## Risks
-
```

## Example Level 3 Operating Cycle

Task:
Update a workflow document without product code changes.

Pre-task intake:
1. Read `ROADMAP.md`.
2. Read `NEXT_TASK.md`.
3. Read `ACTIVE_TASKS.md`.
4. Read `COMPLETED_TASKS.md`.
5. Read `CODEX_STATE.md`.

Execution:
1. Classify the task as `Dev Workflow`.
2. Record the in-progress task in `ACTIVE_TASKS.md`.
3. Edit only approved workflow files.
4. Run `git status`, `git diff --stat`, and `git diff --check`.
5. Confirm the success scenario: requested docs exist, state files exist, product code is untouched, and validation passes.

Post-task state update:
1. Remove or complete the task in `ACTIVE_TASKS.md`.
2. Add the task result to `COMPLETED_TASKS.md`.
3. Refresh `NEXT_TASK.md` with 1-3 independent next tasks.
4. Refresh `CODEX_STATE.md` with phase, priorities, blockers, recommended work lanes, last completed task, and current workflow level.
5. Report the required Level 3 completion fields.

## Recommended First Level 3 Task Batch

1. Dev Workflow: Implement and validate `./tes dev --demo-run` as the first outcome-tested operating-loop task.
2. Tests/Documentation: Document the Level 3 intake and completion-report expectations in contributor-facing docs after the workflow loop proves stable.
3. Dashboard/UI: Inspect dashboard run/replay flows and identify the smallest independent UI validation gap before implementation.
