# Codex Validation

This document defines validation expectations for Codex work on TES. Validation is now Level 3: Objective-Driven Planning. Tests and builds are required gates, success scenarios define completion, and objective progress must be refreshed after completed or blocked tasks.

## Required Commands

Use the commands that match the approved task scope:

```bash
./tes check
./tes check python
./tes check python-release
cd web && npm run build
```

Level 3 state-only or workflow-doc tasks should run the requested repository hygiene checks:

```bash
git status
git diff --stat
git diff --check
```

## Selection Rules

- Broad repository, engine, integration, or cross-layer changes: run `./tes check`.
- Python-only changes: run at least `./tes check python-release`.
- Web changes: run `cd web && npm run build`.
- Docs-only workflow changes: full build is optional; at minimum, run `git status`, `git diff --stat`, and `git diff --check` when requested.
- Objective/state-only Level 3 maintenance: run `git status`, `git diff --stat`, and `git diff --check` unless a broader validation command is requested.
- Do not claim success for commands that were not run.

## Objective-Driven Validation

Codex must validate more than the local task diff. It must validate whether the task advanced the selected objective and milestone.

Before work:
- Read `OBJECTIVES.md` first.
- Identify the objective, current milestone, status, progress, risks, dependencies, and validation criteria.
- Confirm the task is not duplicate completed work.

During work:
- Run the validation command appropriate to the approved scope.
- Execute the success scenario.
- Observe actual workflow evidence, not only build or test output.

After work:
- Update objective or milestone progress when evidence changes.
- Record blockers if validation cannot complete.
- Recommend Top 3 next tasks with Impact, Risk, Dependencies, and Lane.

## Level 3 Objective-Driven Loop Validation

Codex must not stop merely because code compiles, tests pass, or services start. Those results are necessary evidence, not completion.

For every task, validate the requested user workflow through the task's mandatory `Success Scenario`, then update objective and project state.

The required loop is:

1. Read `OBJECTIVES.md`, `ROADMAP.md`, `NEXT_TASK.md`, `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, and `CODEX_STATE.md`.
2. Confirm objective, milestone, task scope, work lane, file ownership, validation target, and success scenario.
3. Implement only the approved change.
4. Run tests or validation commands appropriate to the task.
5. Execute the user workflow described in the success scenario.
6. Observe failures.
7. Repair failures within the approved scope.
8. Retest.
9. Repeat until the success scenario succeeds or a blocker prevents completion.
10. Update objective progress and milestone status when evidence changes.
11. Update `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.

The loop ends only when:
- The requested user workflow succeeds and state files are updated.
- Or a documented blocker prevents completion and state files record the blocker.

## Objective Progress Validation

Objective progress must be evidence-based.

Valid progress evidence includes:
- A milestone validation command passed.
- A success scenario step was executed and observed.
- A blocker was reproduced and documented.
- A dependency was removed.
- A stale recommendation was retired because the work is already complete.

Invalid progress evidence includes:
- Planning text without executed validation.
- Assumptions about behavior not observed.
- A service start without checking the user-visible workflow.
- Documentation that describes functionality before functionality exists.

## Milestone Validation

A milestone is `Complete` only when:
- Its validation criteria have current evidence.
- Related tasks are complete or intentionally deferred.
- Remaining risks do not block the milestone's stated outcome.

A milestone is `Blocked` when:
- Its next validation step cannot run because of missing credentials, unavailable services, missing dependencies, insufficient permissions, unavailable local data, or an external prerequisite.

A milestone remains `Active` when:
- Work has begun but the validation criteria are not yet satisfied.

A milestone remains `Not Started` when:
- No current work or validation evidence exists.

## Success Scenario Validation

Each task must include a `Success Scenario` section. Codex must execute the listed steps after implementation and test validation whenever the environment allows it.

Completion requires every step to succeed. If a step cannot be executed, Codex must document the blocker and stop only after explaining what is needed to complete the scenario.

## State Update Validation

After every completed Level 3 task, Codex must validate that state updates occurred:

- `OBJECTIVES.md` reflects objective and milestone progress when changed.
- `ACTIVE_TASKS.md` no longer lists the completed task as active, or marks it blocked with a clear blocker.
- `COMPLETED_TASKS.md` contains the completed task, success scenario result, files changed, validation run, objective status, and follow-up.
- `NEXT_TASK.md` recommends 1-3 objective-aware next tasks.
- `CODEX_STATE.md` reflects current project phase, current priorities, known blockers, recommended work lanes, last completed task, and current workflow level.

## Task Recommendation Validation

Recommended next tasks must:

- Include exactly 1-3 tasks when possible.
- Identify Objective and Milestone.
- Include Impact, Risk, Dependencies, and Lane.
- Prefer unblockers first.
- Prefer infrastructure required by multiple milestones.
- Prefer user-visible functionality before automation.
- Prefer automation before documentation.
- Avoid duplicate tasks, completed work, low-value busywork, and documentation before functionality.
- Avoid overlapping file ownership unless the user explicitly approves integration work.
- Include a validation target or success scenario summary.

## Blocker Rules

Report a blocker when the success scenario cannot be completed because of a prerequisite Codex cannot satisfy within the approved scope.

For blockers, report:
- Blocked success scenario step.
- Command or action attempted.
- Observed error or missing prerequisite.
- Reason the blocker cannot be resolved within scope.
- Recommended next action.

## Stop Conditions

Stop and ask the user when:
- A fix requires files outside the approved scope.
- A fix requires product behavior changes not requested by the task.
- Matching behavior would change without explicit approval.
- A dependency would need to be added.
- Validation failures appear unrelated to the task.
- The repository instructions conflict with the requested action.
- The success scenario is blocked by missing credentials, unavailable services, missing dependencies, insufficient permissions, or another prerequisite outside the approved scope.

## Completion Report Validation Section

Use this validation format:

```markdown
## Validation
- `git status`: passed / failed / not run
- `git diff --stat`: passed / failed / not run
- `git diff --check`: passed / failed / not run
- `./tes check`: passed / failed / not run
- `./tes check python`: passed / failed / not run
- `./tes check python-release`: passed / failed / not run
- `cd web && npm run build`: passed / failed / not run
```

Only mark a command as passed when it was actually run and exited successfully.

## Required Objective Status Section

Use this format for Level 3 tasks:

```markdown
## OBJECTIVE STATUS

Objective:

Current milestone:

Progress:

Remaining milestones:

Blockers:

Recommended next tasks:
```

## Required Completion Report Level 3 Section

Use this format for Level 3 tasks:

```markdown
## LEVEL 3 COMPLETION REPORT

Completed task:

Success scenario result:

Files changed:

Validation results:

State updates:

Recommended next tasks:
```

The `Validation results` field should cite concrete command results. The `Success scenario result` field should cite concrete outputs such as file paths, logs, screenshots, generated artifacts, or observed UI state.
