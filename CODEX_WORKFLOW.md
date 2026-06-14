# Codex Workflow

This document defines how Codex should operate on Tirrad Exchange System (TES). The goal is controlled, iterative work that preserves deterministic behavior, strict contracts, and clear human review points.

## Roles

- ChatGPT: architect, task framer, and reviewer. ChatGPT should help shape the work, identify risks, and review outcomes before merge decisions.
- Codex: local implementation worker. Codex investigates, edits, tests, and reports within the approved task scope.
- User: final verifier and merge approver. The user decides what is accepted, merged, released, or deferred.

## Environment Assumptions

- Primary local environment is Windows.
- Shell usage may include PowerShell or Git Bash, but commands should be reported exactly as run.
- Visual Studio may be used for C++ or solution-level inspection, but `./tes` remains the repository workflow entry point.
- The matching engine in `engine/` remains the source of truth for execution behavior.
- The web application, when touched, must be validated with `cd web && npm run build`.

## Workflow Levels

### Level 1: Task Execution

Status: baseline behavior.

Level 1 means Codex executes the approved task scope, runs the requested validation commands, and reports the result. Level 1 is not sufficient for completion when the user asked for a working workflow or observable outcome.

Level 1 completion is limited to task execution evidence such as changed files, passing tests, or successful builds. It does not prove the requested user workflow succeeds.

### Level 2: Outcome Validation

Status: active for future Codex tasks.

Level 2 means Codex must validate the requested user outcome, not only the implementation task. Every future task must include a mandatory `Success Scenario` section that describes the concrete workflow that proves the requested outcome works.

At Level 2, a task is not complete because:
- Code compiles.
- Tests pass.
- Services start.

At Level 2, a task is complete only when:
- The requested user workflow succeeds according to the task's `Success Scenario`.
- Or a documented blocker prevents completion.

Codex must continue through the validation loop until one of those completion conditions is true.

### Level 3: Roadmap and State Maintenance

Status: documented only. Requires human approval before use.

Level 3 allows Codex to maintain project state files such as `ROADMAP.md` and `NEXT_TASK.md` after completing approved tasks. Codex may suggest updates, but the user must approve use of this level before Codex treats roadmap maintenance as part of normal work.

### Level 4: Issue and PR Operating Loop

Status: documented only. Requires human approval before use.

Level 4 allows Codex to operate from issues or pull requests, inspect review feedback, make scoped updates, run validation, and prepare PR-ready reports. Codex must not create commits, push branches, or open pull requests unless the user explicitly permits those actions for the specific task.

### Level 5: Future Multi-Agent Orchestration

Status: documented only. Requires human approval before use.

Level 5 is reserved for future coordinated work across independent task lanes. Parallel tasks must have disjoint file ownership. Shared files require a single owning task, and integration work must happen last.

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
- Never claim tests passed unless they were actually run.

## Test-Fix-Retest Loop

When validation fails:
- Read the failure carefully before editing.
- Fix only failures related to the approved task.
- Re-run the relevant failing command after each fix.
- If unrelated failures are found, report them clearly and do not edit unrelated files.
- If the same failure repeats after reasonable investigation, stop and ask for guidance.

## Level 2 Validation Loop

For Level 2 tasks, Codex must run this loop:

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
- Codex must not commit or push for Level 1 tasks unless explicitly instructed.
- Commit messages must use Conventional Commits when commits are approved.
- Branch names must not use `codex/` prefixes.
- Pushing, PR creation, and merge actions require explicit user approval for the specific action.

## Reporting Requirements

Every completion report must include:
- Files changed.
- Validation commands run.
- Validation results.
- Success scenario steps executed.
- Observed result.
- Evidence.
- Remaining issues.
- Blockers.
- Risks or unresolved questions.
- Next recommended task.

Codex should also report when no validation was run and explain why.

## Required Level 2 Completion Report Section

Every Level 2 completion report must include:

```markdown
## SUCCESS SCENARIO

Steps executed:

Observed result:

Evidence:

Remaining issues:

Blockers:

Recommended next task:
```

## Updating NEXT_TASK.md

At Level 1 or Level 2, Codex may update `NEXT_TASK.md` only when the task explicitly includes it or the workflow task requires it.

At Levels 3-5, `NEXT_TASK.md` maintenance requires human approval before use. Updates should keep the next task small, concrete, and validation-ready.

## Standard Completion Report

```markdown
## Summary
- 

## Files Changed
- 

## Validation
- [ ] `git status`
- [ ] `git diff --stat`
- [ ] Other commands actually run:

## SUCCESS SCENARIO
Steps executed:

Observed result:

Evidence:

Remaining issues:

Blockers:

Recommended next task:

## Risks
- 

## Next Recommended Task
- 
```

## Standard Codex Prompt Template

```markdown
Task:

Goal:

Allowed files:

Do not edit:

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
