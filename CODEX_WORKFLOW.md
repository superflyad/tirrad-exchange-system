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

### Level 1: Single-Task Iteration

Status: active now.

Level 1 is the default operating mode for Codex. Each task should have a clear scope, a small set of allowed files, a validation plan, and a completion report. Codex may investigate and edit only within the requested scope.

Recommended first Level 1 task: add `./tes dev` as a repository workflow command after human approval of that task.

### Level 2: Roadmap and State Maintenance

Status: documented only. Requires human approval before use.

Level 2 allows Codex to maintain project state files such as `ROADMAP.md` and `NEXT_TASK.md` after completing approved tasks. Codex may suggest updates, but the user must approve use of this level before Codex treats roadmap maintenance as part of normal work.

### Level 3: Issue and PR Operating Loop

Status: documented only. Requires human approval before use.

Level 3 allows Codex to operate from issues or pull requests, inspect review feedback, make scoped updates, run validation, and prepare PR-ready reports. Codex must not create commits, push branches, or open pull requests unless the user explicitly permits those actions for the specific task.

### Level 4: Future Multi-Agent Orchestration

Status: documented only. Requires human approval before use.

Level 4 is reserved for future coordinated work across independent task lanes. Parallel tasks must have disjoint file ownership. Shared files require a single owning task, and integration work must happen last.

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
- Risks or unresolved questions.
- Next recommended task.

Codex should also report when no validation was run and explain why.

## Updating NEXT_TASK.md

At Level 1, Codex may update `NEXT_TASK.md` only when the task explicitly includes it or the workflow task requires it.

At Levels 2-4, `NEXT_TASK.md` maintenance requires human approval before use. Updates should keep the next task small, concrete, and validation-ready.

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

Permissions:
- Do not commit.
- Do not push.
- Stop after report.
```
