# Codex Task Template

Use this template for Codex tasks. Level 3 Objective-Driven Planning is active for future work: tasks must be selected from project objectives, tied to milestones, validated through success scenarios, and reflected back into project state.

```markdown
Task:

Goal:

Workflow level:
- Level 3: Objective-Driven Planning

Mode:
- Investigation-only / Edit

Required pre-task objective and state intake:
- [ ] Read `OBJECTIVES.md`
- [ ] Read `ROADMAP.md`
- [ ] Read `NEXT_TASK.md`
- [ ] Read `ACTIVE_TASKS.md`
- [ ] Read `COMPLETED_TASKS.md`
- [ ] Read `CODEX_STATE.md`

Objective:
- Title:
- Current Status:
- Progress %:

Milestone:
- Name:
- Status: Not Started / Active / Blocked / Complete
- Validation Criteria:

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

Task generation and ranking:
- [ ] Confirm the task advances or unblocks the named milestone.
- [ ] Reject duplicate work already completed.
- [ ] Prefer unblockers, shared infrastructure, user-visible functionality, automation, then documentation.
- [ ] Record Impact, Risk, Dependencies, and Lane for recommended follow-ups.

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
- [ ] Update `OBJECTIVES.md` if objective or milestone progress changed.
- [ ] Update `ACTIVE_TASKS.md`
- [ ] Update `COMPLETED_TASKS.md`
- [ ] Update `NEXT_TASK.md`
- [ ] Update `CODEX_STATE.md`

Top 3 next tasks:
1. Title:
   - Objective:
   - Milestone:
   - Impact:
   - Risk:
   - Dependencies:
   - Lane:
2. Title:
   - Objective:
   - Milestone:
   - Impact:
   - Risk:
   - Dependencies:
   - Lane:
3. Title:
   - Objective:
   - Milestone:
   - Impact:
   - Risk:
   - Dependencies:
   - Lane:

Acceptance:
-

Permissions:
- Do not commit.
- Do not push.
- Stop after completion report.

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

## OBJECTIVE STATUS
Objective:

Current milestone:

Progress:

Remaining milestones:

Blockers:

Recommended next tasks:

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

## Example Level 3 Objective-Driven Cycle

Task:
Outcome-validate a milestone in the One-command local onboarding objective.

Pre-task intake:
1. Read `OBJECTIVES.md` first.
2. Identify the active objective, current milestone, objective progress, risks, and dependencies.
3. Read `ROADMAP.md`, `NEXT_TASK.md`, `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, and `CODEX_STATE.md`.

Execution:
1. Classify the task by lane.
2. Record the in-progress task in `ACTIVE_TASKS.md`.
3. Edit only approved files.
4. Run the selected validation command.
5. Execute the success scenario.
6. Record whether the milestone advanced, completed, or blocked.

Post-task state update:
1. Update `OBJECTIVES.md` when evidence changes objective or milestone progress.
2. Remove or block the task in `ACTIVE_TASKS.md`.
3. Add the result to `COMPLETED_TASKS.md`.
4. Refresh `NEXT_TASK.md` with the Top 3 objective-aware recommendations.
5. Refresh `CODEX_STATE.md` with phase, priorities, blockers, lanes, last completed task, and workflow level.
6. Report objective status and Level 3 completion fields.

## Recommended First Level 3 Objective-Driven Task Batch

1. Dev Workflow: Outcome-validate `./tes dev --demo-run` against the One-command local onboarding objective.
2. Dashboard/UI: Verify generated demo runs are visible in dashboard run detail and replay views after startup validation succeeds.
3. Tests/Documentation: Add automated smoke validation or contributor guidance only after the executable workflow has current evidence.
