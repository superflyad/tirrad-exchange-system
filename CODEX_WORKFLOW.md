# Codex Workflow

This document defines how Codex should operate on Tirrad Exchange System (TES). The goal is controlled, iterative work that preserves deterministic behavior, strict contracts, project memory, and clear human review points.

## Roles

- ChatGPT: architect, task framer, and reviewer. ChatGPT should help shape objectives, identify risks, and review outcomes before merge decisions.
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

### Level 2: Outcome Validation

Status: superseded by Level 3.

Level 2 means Codex validates the requested user outcome, not only the implementation task. Every task must include a mandatory `Success Scenario` section that describes the concrete workflow that proves the requested outcome works.

At Level 2, a task is complete only when:
- The requested user workflow succeeds according to the task's `Success Scenario`.
- Or a documented blocker prevents completion.

### Level 3: Objective-Driven Planning

Status: active for future Codex tasks.

Level 3 keeps Level 2 outcome validation and the project operating loop, then adds objective-driven planning. Codex must reason from project objectives before selecting isolated tasks. `NEXT_TASK.md` is no longer the planning source of truth; it is the short-form recommendation derived from `OBJECTIVES.md`.

Objective-Driven Planning means Codex follows this chain:

```text
Objective -> Milestone -> Task -> Validation -> Progress
```

- Objective: a project outcome with success criteria, risks, dependencies, milestone status, and progress.
- Milestone: a meaningful step toward an objective with status, related tasks, and validation criteria.
- Task: a scoped unit of work selected because it advances or unblocks a milestone.
- Validation: the tests, checks, and success scenario proving the task advanced the milestone without violating TES contracts.
- Progress: the objective and milestone status update recorded after work completes or blocks.

At Level 3, every task starts with objective intake and ends with objective progress reporting.

Before every future task, Codex must read:
- `OBJECTIVES.md`
- `ROADMAP.md`
- `NEXT_TASK.md`
- `ACTIVE_TASKS.md`
- `COMPLETED_TASKS.md`
- `CODEX_STATE.md`

After every completed or blocked task, Codex must update, when relevant:
- `OBJECTIVES.md`
- `ACTIVE_TASKS.md`
- `COMPLETED_TASKS.md`
- `NEXT_TASK.md`
- `CODEX_STATE.md`

`ROADMAP.md` remains the long-running planning source. Codex reads it before work and may recommend updates, but should edit it only when the task explicitly includes roadmap maintenance or objective structure alignment.

Level 3 planning files do not authorize product code changes, matching behavior changes, commits, pushes, or pull requests.

### Level 4: Parallel Task Execution

Status: documented only. Do not enable without explicit human approval.

Level 4 will allow multiple objective-derived tasks to proceed in parallel only when file ownership is disjoint and validation boundaries are clear. Shared files require a single owning task, and integration work must happen last.

### Level 5: Multi-Agent Orchestration

Status: documented only. Do not enable without explicit human approval.

Level 5 will allow coordinated multi-agent work across objectives, milestones, and lanes. It must preserve strict file ownership, deterministic validation, and a single integration authority.

## Objective Structure

Every objective in `OBJECTIVES.md` must contain:

- Title
- Description
- Success Criteria
- Milestones
- Current Status
- Progress %
- Known Risks
- Dependencies

Objective status should be one of:
- Not Started
- Active
- Blocked
- Complete

Progress percentage should be evidence-based. Do not inflate progress because planning exists. Prefer simple milestone-weighted progress unless the objective defines a different measure.

## Milestone Structure

Every milestone must contain:

- Name
- Description
- Status
- Related Tasks
- Validation Criteria

Milestone status must be one of:
- Not Started
- Active
- Blocked
- Complete

Milestones are complete only when their validation criteria have current evidence or a blocker is documented and accepted as the outcome for that task.

## Work Lanes

Use these lanes when classifying objectives, active work, completed work, and recommended tasks:

- Core/API: engine behavior, Python models, serialization contracts, API services, persistence, execution queue, and public command/event surfaces.
- Dashboard/UI: web dashboard pages, components, live monitoring, replay views, run browsing, and UI validation.
- Dev Workflow: `./tes` workflow commands, local development scripts, CI wiring, repository automation, and Codex operating docs.
- Tests/Documentation: test coverage, examples, docs, contributor guidance, and validation documentation.

Codex should recommend tasks by lane and call out when a milestone depends on multiple lanes.

## Task Generation Rules

When generating candidate tasks, Codex must:

1. Read `OBJECTIVES.md` first.
2. Determine objective status.
3. Determine milestone status.
4. Identify missing work, blockers, stale evidence, or validation gaps.
5. Generate candidate tasks that advance a specific milestone.
6. Rank tasks by project impact.
7. Update `NEXT_TASK.md` with the highest-value 1-3 recommendations.

Candidate tasks must include:
- Objective
- Milestone
- Lane
- Impact
- Risk
- Dependencies
- File ownership
- Validation target
- Success scenario summary

## Prioritization Rules

Prefer work in this order:

1. Unblockers
2. Infrastructure required by multiple milestones
3. User-visible functionality
4. Automation
5. Documentation

Avoid:
- Duplicate tasks
- Completed work
- Low-value busywork
- Documentation before functionality, unless the objective itself is workflow or documentation governance

## Recommendation Rules

Every completed task must provide Top 3 next tasks. Each recommendation must include:

- Impact
- Risk
- Dependencies
- Lane

Recommendations should be objective-aware. A good recommendation explains which objective and milestone it advances, not only which file it changes.

## Level 3 Operating Cycle

Use this cycle for every future Level 3 task:

1. Read `OBJECTIVES.md`, `ROADMAP.md`, `NEXT_TASK.md`, `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, and `CODEX_STATE.md`.
2. Select the active objective and milestone, or identify that the user supplied a new objective.
3. Confirm task scope, work lane, file ownership, success scenario, and validation target.
4. Mark or update the task in `ACTIVE_TASKS.md` when work begins.
5. Implement only the approved change.
6. Run validation commands appropriate to the task.
7. Execute the task's `Success Scenario`.
8. Repair failures within the approved scope and retest.
9. Update objective and milestone progress when evidence changes.
10. Update `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.
11. Report completion using the required Level 3 objective-driven report fields.

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

Codex must identify and report blockers instead of pretending completion. For each blocker, report:
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
- Objective status.

Codex should also include blockers, remaining issues, risks, and unresolved questions when applicable. Codex should report when no validation was run and explain why.

## Required Objective Status Section

Every completed Level 3 task must include:

```markdown
## OBJECTIVE STATUS

Objective:

Current milestone:

Progress:

Remaining milestones:

Blockers:

Recommended next tasks:
```

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

At Level 3, Codex must update `NEXT_TASK.md` after every completed task. `NEXT_TASK.md` should be derived from `OBJECTIVES.md`, limited to 1-3 high-value recommendations, and should not become the long-form planning source.

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

## Standard Codex Prompt Template

```markdown
Task:

Goal:

Allowed files:

Do not edit:

Workflow level:
- Level 3: Objective-Driven Planning

Mode:
- Investigation-only / Edit

Objective:

Milestone:

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
