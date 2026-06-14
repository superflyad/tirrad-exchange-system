# Codex State

This file is the compact Level 3 operating snapshot for TES. Codex must read it before every future task and update it after every completed or blocked task.

## Current Workflow Level

Level 3: Objective-Driven Planning

## Current Project Phase

Objective-driven workflow hardening and local onboarding validation.

## Active Planning Model

```text
Objective -> Milestone -> Task -> Validation -> Progress
```

Codex must read `OBJECTIVES.md` before `NEXT_TASK.md`, derive candidate tasks from objective and milestone status, and keep progress evidence-based.

## Current Priorities

1. Prove the existing `./tes dev --demo-run` workflow through current end-to-end outcome evidence.
2. Track the One-command local onboarding objective through milestones, validation criteria, and progress updates.
3. Keep strict command and event contracts intact across simulation, API, analytics, and serialization boundaries.
4. Prefer small, independent tasks with clear file ownership and observable success scenarios.
5. Preserve `./tes` as the single workflow entry point for build, test, and local development operations.

## Current Project Status

- Level 3 Objective-Driven Planning is active.
- `OBJECTIVES.md` is the first planning input.
- No active task is currently in progress.
- `./tes dev --demo-run` is implemented in the repository and documented for local development.
- The highest-value next task is outcome validation of the existing workflow against the One-command local onboarding objective.
- `NEXT_TASK.md` now contains objective-derived Top 3 recommendations instead of acting as the sole planning source.

## Active Objective

- Objective: One-command local onboarding
- Current status: Active
- Progress: 35%
- Current milestones: Build verification and Unified local startup are active; Python verification, Outcome validation, and Automated smoke validation are not started.
- Blockers: No known active blocker. Current evidence gap is unvalidated local outcome behavior on this machine.

## Completed Capabilities

- Level 2 Outcome Validation workflow documentation.
- Level 3 Project Operating Loop state files and maintenance rules.
- Level 3 Objective-Driven Planning docs and objective model.
- Root `./tes` workflow entry point for checks, API commands, local development startup, and demo-run startup.
- API demo-run helper that prints run and replay URLs.
- Dashboard run, live monitor, and replay surfaces documented and present in the codebase.

## Missing Capabilities

- Current recorded evidence that `./tes dev --demo-run` succeeds end to end on this machine.
- Current recorded evidence that the generated run appears in the dashboard run list and that replay pages load for the printed `run_id`.
- Automated smoke validation for the one-command onboarding outcome.
- Contributor-facing Level 3 objective-driven usage documentation outside the internal workflow/state files.

## Known Blockers

No known active blockers.

## Recommended Work Lanes

- Dev Workflow: Highest immediate priority. Outcome-validate the existing `./tes dev --demo-run` path and capture evidence.
- Dashboard/UI: Verify generated run detail and replay visibility after local startup evidence exists.
- Tests/Documentation: Define or implement automated smoke validation after the executable workflow has current evidence.
- Core/API: Keep available for contract-safe API or serialization fixes, but avoid touching matching behavior without explicit approval.

## Last Completed Task

Upgrade workflow to Objective-Driven Planning.

## Operating Notes

- Before every future task, read `OBJECTIVES.md`, `ROADMAP.md`, `NEXT_TASK.md`, `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, and `CODEX_STATE.md`.
- After every completed task, update `OBJECTIVES.md` when progress changes, then update `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.
- Recommended next tasks must include Impact, Risk, Dependencies, and Lane.
- Prefer unblockers, shared infrastructure, user-visible functionality, automation, then documentation.
- Avoid duplicate tasks, completed work, low-value busywork, and documentation before functionality unless the objective is workflow governance.
- Do not commit or push unless the user explicitly approves that action for the specific task.
