# Codex State

This file is the compact Level 3 operating snapshot for TES. Codex must read it before every future task and update it after every completed task.

## Current Workflow Level

Level 3: Project Operating Loop

## Current Project Phase

Workflow hardening and local operating-loop setup.

## Current Priorities

1. Prove the Level 3 operating loop with one concrete, outcome-validated workflow task.
2. Keep strict command and event contracts intact across simulation, API, analytics, and serialization boundaries.
3. Prefer small, independent tasks with clear file ownership and observable success scenarios.
4. Preserve `./tes` as the single workflow entry point for build, test, and local development operations.

## Known Blockers

No known active blockers.

## Recommended Work Lanes

- Dev Workflow: Highest immediate priority. Implement and validate the first Level 3 task through `./tes dev --demo-run`.
- Tests/Documentation: Support workflow changes with discoverable tests and contributor-facing docs once behavior is implemented.
- Dashboard/UI: Validate dashboard run and replay workflows after the dev workflow can start the required surfaces.
- Core/API: Keep available for contract-safe API or serialization fixes, but avoid touching matching behavior without explicit approval.

## Last Completed Task

Upgrade Codex workflow documentation and state files from Level 2 Outcome Validation to Level 3 Project Operating Loop.

## Operating Notes

- Before every future task, read `ROADMAP.md`, `NEXT_TASK.md`, `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, and `CODEX_STATE.md`.
- After every completed task, update `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.
- Recommended next tasks must be limited to 1-3 tasks, prefer high impact, prefer independent work, and avoid overlapping file ownership.
- Do not commit or push unless the user explicitly approves that action for the specific task.
