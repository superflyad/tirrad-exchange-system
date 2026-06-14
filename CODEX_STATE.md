# Codex State

This file is the compact Level 3 operating snapshot for TES. Codex must read it before every future task and update it after every completed task.

## Current Workflow Level

Level 3: Project Operating Loop

## Current Project Phase

Workflow hardening and local operating-loop validation.

## Current Priorities

1. Prove the existing `./tes dev --demo-run` workflow through current end-to-end outcome evidence.
2. Keep strict command and event contracts intact across simulation, API, analytics, and serialization boundaries.
3. Prefer small, independent tasks with clear file ownership and observable success scenarios.
4. Preserve `./tes` as the single workflow entry point for build, test, and local development operations.

## Current Project Status

- Level 3 Project Operating Loop is active.
- No active task is currently in progress.
- `./tes dev --demo-run` is implemented in the repository and documented for local development.
- The stale state item was the repeated recommendation to implement `./tes dev --demo-run`; the correct next task is outcome validation of the existing workflow.
- Duplicate task language was consolidated around one next action: validate the demo-run workflow before documentation or dashboard follow-up work.

## Completed Capabilities

- Level 2 Outcome Validation workflow documentation.
- Level 3 Project Operating Loop state files and maintenance rules.
- Root `./tes` workflow entry point for checks, API commands, local development startup, and demo-run startup.
- API demo-run helper that prints run and replay URLs.
- Dashboard run, live monitor, and replay surfaces documented and present in the codebase.

## Missing Capabilities

- Current recorded evidence that `./tes dev --demo-run` succeeds end to end on this machine.
- Current recorded evidence that the generated run appears in the dashboard run list and that replay pages load for the printed `run_id`.
- Contributor-facing Level 3 usage documentation outside the internal workflow/state files.
- A scoped dashboard validation-gap report after the demo-run workflow is outcome-validated.

## Known Blockers

No known active blockers.

## Recommended Work Lanes

- Dev Workflow: Highest immediate priority. Outcome-validate the existing `./tes dev --demo-run` path and capture evidence.
- Tests/Documentation: Document Level 3 contributor usage after the executable workflow has current evidence.
- Dashboard/UI: Inspect run/replay validation gaps after the dev workflow validation is complete.
- Core/API: Keep available for contract-safe API or serialization fixes, but avoid touching matching behavior without explicit approval.

## Last Completed Task

Validate Level 3 state operating loop and refresh stale planning state.

## Operating Notes

- Before every future task, read `ROADMAP.md`, `NEXT_TASK.md`, `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, and `CODEX_STATE.md`.
- After every completed task, update `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.
- Recommended next tasks must be limited to 1-3 tasks, prefer high impact, prefer independent work, and avoid overlapping file ownership.
- Do not commit or push unless the user explicitly approves that action for the specific task.
