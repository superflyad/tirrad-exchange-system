# Codex Workflow

This document defines how Codex should operate on Tirrad Exchange System (TES). The goal is controlled, iterative work that preserves deterministic behavior, strict contracts, project memory, and clear human review points.

## Roles

- ChatGPT: architect, task framer, and reviewer. ChatGPT should help shape the work, identify risks, and review outcomes before merge decisions.
- Codex: local implementation worker. Codex investigates, edits, tests, maintains approved project state, and reports within the approved task scope.
- User: final verifier and merge approver. The user decides what is accepted, merged, released, or deferred.

## Environment Assumptions

- Primary local environment is Windows.
- Shell usage may include PowerShell or Git Bash, but commands should be reported exactly as run.
- Visual Studio may be used for C++ or solution-level inspection, but `./tes` remains the repository workflow entry point.
- The matching engine in `engine/` remains the source of truth for execution behavior.
- The web application, when touched, must be validated with `cd web && npm run build`.

## Workflow Levels

### Level 1: Task Execution

Status: historical baseline.

Level 1 means Codex executes the approved task scope, runs the requested validation commands, and reports the result. Level 1 is not sufficient for completion when the user asked for a working workflow or observable outcome.

Level 1 completion is limited to task execution evidence such as changed files, passing tests, or successful builds. It does not prove the requested user workflow succeeds.

### Level 2: Outcome Validation

Status: superseded by Level 3.

Level 2 means Codex validates the requested user outcome, not only the implementation task. Every task must include a mandatory `Success Scenario` section that describes the concrete workflow that proves the requested outcome works.

At Level 2, a task is not complete because:
- Code compiles.
- Tests pass.
- Services start.

At Level 2, a task is complete only when:
- The requested user workflow succeeds according to the task's `Success Scenario`.
- Or a documented blocker prevents completion.

Codex must continue through the validation loop until one of those completion conditions is true.

### Level 3: Project Operating Loop

Status: active for future Codex tasks.

Level 3 keeps Level 2 outcome validation and adds project state maintenance. Codex must maintain lightweight state files so future tasks can start from the current project status, recent work, known blockers, and recommended next work without requiring the user to restate context.

At Level 3, every future task starts with a state intake and ends with a state update.

Before every future task, Codex must read:
- `ROADMAP.md`
- `NEXT_TASK.md`
- `ACTIVE_TASKS.md`
- `COMPLETED_TASKS.md`
- `CODEX_STATE.md`

After every completed task, Codex must update:
- `ACTIVE_TASKS.md`
- `COMPLETED_TASKS.md`
- `NEXT_TASK.md`
- `CODEX_STATE.md`

Level 3 state files are planning and coordination artifacts. They do not authorize product code changes, matching behavior changes, commits, pushes, or pull requests.

### Level 4: Issue and PR Operating Loop

Status: documented only. Requires human approval before use.

Level 4 allows Codex to operate from issues or pull requests, inspect review feedback, make scoped updates, run validation, and prepare PR-ready reports. Codex must not create commits, push branches, or open pull requests unless the user explicitly permits those actions for the specific task.

### Level 5: Future Multi-Agent Orchestration

Status: documented only. Requires human approval before use.

Level 5 is reserved for future coordinated work across independent task lanes. Parallel tasks must have disjoint file ownership. Shared files require a single owning task, and integration work must happen last.

## Level 3 State Files

`CODEX_STATE.md` is the compact operating snapshot. It must track:
- Current project phase.
- Current priorities.
- Known blockers.
- Recommended work lanes.
- Last completed task.
- Current workflow level.

`ACTIVE_TASKS.md` tracks tasks currently in progress, blocked, or ready to resume. It should include task name, lane, status, owner if known, file ownership, validation target, and blocker if any.

`COMPLETED_TASKS.md` tracks completed tasks in reverse chronological order. Each entry should include completed task, date, lane, files changed, validation run, success scenario result, state updates, and recommended follow-up.

`NEXT_TASK.md` tracks the highest-signal recommended next work. It should stay small, concrete, scoped, validation-ready, and consistent with Level 3 task recommendation rules.

`ROADMAP.md` remains the long-running planning source. Codex reads it before work and may recommend updates, but it should not edit it unless the task explicitly includes roadmap maintenance.

## Work Lanes

Use these lanes when classifying active, completed, and recommended tasks:

- Core/API: engine behavior, Python models, serialization contracts, API services, persistence, execution queue, and public command/event surfaces.
- Dashboard/UI: web dashboard pages, components, live monitoring, replay views, run browsing, and UI validation.
- Dev Workflow: `./tes` workflow commands, local development scripts, CI wiring, repository automation, and Codex operating docs.
- Tests/Documentation: test coverage, examples, docs, contributor guidance, and validation documentation.

## Task Recommendation Rules

When recommending future work, Codex must:
- Recommend 1-3 next tasks.
- Prefer highest-impact tasks.
- Prefer independent tasks.
- Avoid overlapping file ownership.
- Identify the lane for each recommended task.
- Include the expected validation command or success scenario.
- Avoid recommending product code changes that would weaken strict contracts or alter matching behavior without explicit approval.

## Operating Modes

### Investigation-Only Mode

Use investigation-only mode when the user asks Codex to inspect, explain, plan, review, or assess without making changes.

Rules:
- Do not edit files.
- Do not stage, commit, push, or open PRs.
- Report findings with file paths, risks, and recommended next steps.
- If a fix is obvious, describe it rather than applying it.

### Edit Mode

Use edit mode only when the user asks Codex to make a change or clearly assigns an implementation task.

Rules:
- Stay within the requested file scope.
- Do not modify product code for workflow-only tasks.
- Do not add dependencies without explicit approval.
- Add or update tests for behavior changes.
- Preserve strict command and event contracts.
- Stop immediately if the task requires files outside the approved scope.

## Level 3 Operating Cycle

Use this cycle for every future Level 3 task:

1. Read `ROADMAP.md`, `NEXT_TASK.md`, `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, and `CODEX_STATE.md`.
2. Confirm the requested task scope, work lane, file ownership, success scenario, and validation target.
3. Mark or update the task in `ACTIVE_TASKS.md` when work begins.
4. Implement only the approved change.
5. Run validation commands appropriate to the task.
6. Execute the task's `Success Scenario`.
7. Repair failures within the approved scope and retest.
8. When the task is complete or blocked, update `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.
9. Report completion using the required Level 3 completion report fields.

Example Level 3 operating cycle:

```markdown
Pre-task intake:
- Read ROADMAP.md, NEXT_TASK.md, ACTIVE_TASKS.md, COMPLETED_TASKS.md, CODEX_STATE.md.
- Select lane: Dev Workflow.
- Confirm file ownership: tes, docs/cli.md, sim/tests/test_tes_root_cli.py.
- Define success scenario: command prints expected help and exits successfully.

Task execution:
- Update ACTIVE_TASKS.md with the in-progress task.
- Implement the scoped workflow change.
- Run the selected validation command.
- Execute the success scenario.

Post-task state update:
- Remove the task from ACTIVE_TASKS.md or mark it blocked.
- Add the result to COMPLETED_TASKS.md.
- Refresh NEXT_TASK.md with 1-3 independent recommendations.
- Refresh CODEX_STATE.md with phase, priorities, blockers, lanes, last completed task, and workflow level.
- Report the completed task, success scenario result, files changed, validation results, state updates, and recommended next tasks.
```

## Validation Commands

Required validation commands that may apply to TES work:

```bash
./tes check
./tes check python
./tes check python-release
cd web && npm run build
```

Validation selection:
- For broad repository changes, prefer `./tes check`.
- For Python-only changes, minimum validation is `./tes check python-release`.
- For web changes, run `cd web && npm run build`.
- For docs-only workflow changes, full build is not required unless Codex chooses to validate more broadly.
- For Level 3 state-only or workflow-doc updates, run `git status`, `git diff --stat`, and `git diff --check` at minimum when requested.
- Never claim tests passed unless they were actually run.

## Test-Fix-Retest Loop

When validation fails:
- Read the failure carefully before editing.
- Fix only failures related to the approved task.
- Re-run the relevant failing command after each fix.
- If unrelated failures are found, report them clearly and do not edit unrelated files.
- If the same failure repeats after reasonable investigation, stop and ask for guidance.

## Level 2 Validation Loop

For Level 2 and Level 3 tasks, Codex must run this loop:

1. Implement the approved change.
2. Run the validation tests appropriate to the task.
3. Execute the user workflow described in the `Success Scenario`.
4. Observe failures in the actual workflow, logs, UI, output files, or command output.
5. Repair failures within the approved scope.
6. Retest the affected validation commands.
7. Repeat until the `Success Scenario` succeeds or a blocker is identified.

Tests are a gate in the loop, not the finish line. Starting a service is also only a gate; the workflow must still be exercised and observed.

Example:

```markdown
Task:
./tes dev --demo-run

Success Scenario:
1. Start stack.
2. Open dashboard.
3. Verify health page.
4. Generate run.
5. Verify run appears.
6. Verify replay data loads.
7. Shut down cleanly.
```

The task is incomplete until all seven steps succeed, or Codex documents a blocker that prevents completion.

## Success Scenario Requirements

Every future task must include a `Success Scenario` section. The section must describe the observable user workflow, not merely internal implementation checks.

A good success scenario names:
- The command, screen, file, or workflow entry point the user will use.
- The ordered steps Codex must execute.
- The expected observable result for each step.
- Any data, fixture, credential, or service dependency needed to perform the workflow.
- The clean shutdown or cleanup step when services are started.

If the requested work is docs-only or investigation-only, the success scenario may be limited to the requested review, documentation update, or report output. It must still define what success looks like for the user.

## Completion Criteria

A task is not complete because:
- Code compiles.
- Tests pass.
- Services start.

A task is complete only when:
- The requested user workflow succeeds.
- Or a documented blocker prevents completion.

When a blocker prevents completion, Codex must still report what was implemented, what validation passed, which success scenario step failed, and what external action is required to unblock the work.

## Blocker Handling

Codex must identify and report blockers instead of pretending completion. Common blockers include:
- Missing credentials.
- External service unavailable.
- Missing dependency.
- Insufficient permissions.
- Required file or dataset unavailable.
- Network access unavailable.
- Environment capability missing, such as no browser for a required UI check.

For each blocker, report:
- The blocked success scenario step.
- The command or action attempted.
- The observed error or missing prerequisite.
- Why Codex cannot resolve it within the approved scope.
- The recommended next action.

## When to Stop and Ask

Codex must stop and ask before continuing when:
- The task requires product code changes outside the approved scope.
- A contract rule would need to be weakened.
- Matching behavior would change without explicit approval.
- A new dependency appears necessary.
- Validation exposes unrelated failures that cannot be separated safely.
- The requested action conflicts with repository instructions.
- The task requires committing, pushing, opening a PR, or merging without explicit permission.

## Commit and Push Permissions

- Codex does not commit or push by default.
- Codex must not commit or push for Level 1, Level 2, or Level 3 tasks unless explicitly instructed.
- Commit messages must use Conventional Commits when commits are approved.
- Branch names must not use `codex/` prefixes.
- Pushing, PR creation, and merge actions require explicit user approval for the specific action.

## Reporting Requirements

Every Level 3 completion report must include:
- Completed task.
- Success scenario result.
- Files changed.
- Validation results.
- State updates.
- Recommended next tasks.

Codex should also include blockers, remaining issues, risks, and unresolved questions when applicable. Codex should report when no validation was run and explain why.

## Required Level 3 Completion Report Section

Every Level 3 completion report must include:

```markdown
## LEVEL 3 COMPLETION REPORT

Completed task:

Success scenario result:

Files changed:

Validation results:

State updates:

Recommended next tasks:
```

## Updating NEXT_TASK.md

At Level 1 or Level 2, Codex may update `NEXT_TASK.md` only when the task explicitly includes it or the workflow task requires it.

At Level 3, Codex must update `NEXT_TASK.md` after every completed task. Updates should keep recommended tasks small, concrete, independent, scoped, validation-ready, and limited to 1-3 recommendations.

## Standard Completion Report

```markdown
## Summary
- 

## Files Changed
- 

## Validation
- [ ] `git status`
- [ ] `git diff --stat`
- [ ] `git diff --check`
- [ ] Other commands actually run:

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

## Standard Codex Prompt Template

```markdown
Task:

Goal:

Allowed files:

Do not edit:

Workflow level:
- Level 3: project operating loop

Mode:
- Investigation-only / Edit

Requirements:
- 

Validation:
- 

Acceptance:
-

Success Scenario:
- 

Permissions:
- Do not commit.
- Do not push.
- Stop after report.
```
