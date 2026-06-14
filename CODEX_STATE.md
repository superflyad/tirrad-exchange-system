# Codex State

This file is the compact Level 3 operating snapshot for TES. Codex must read it before every future task and update it after every completed or blocked task.

## Current Workflow Level

Level 3: Objective-Driven Planning with Project Operations and Capacity Tracking

## Current Project Phase

Objective-driven workflow hardening and local onboarding validation.

## Active Planning Model

```text
Objective -> Milestone -> Task -> Validation -> Progress -> Operations
```

Codex must read `OBJECTIVES.md` and `OPERATIONS.md` before `NEXT_TASK.md`, derive candidate tasks from objective and milestone status, and keep progress, capacity, throughput, blocker, and usage observations evidence-based.

## Current Priorities

1. Prove the existing `./tes dev --demo-run` workflow through current end-to-end outcome evidence.
2. Track the One-command local onboarding objective through milestones, validation criteria, and progress updates.
3. Use Project Operations to answer `What is the highest-value next task?` before recommending work.
4. Keep strict command and event contracts intact across simulation, API, analytics, and serialization boundaries.
5. Prefer small, independent tasks with clear file ownership and observable success scenarios.
6. Preserve `./tes` as the single workflow entry point for build, test, and local development operations.

## Current Project Status

- Level 3 Objective-Driven Planning is active.
- `OBJECTIVES.md` is the first planning input.
- `OPERATIONS.md` defines throughput, capacity, blocker, usage, and value tracking.
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
- Current bottleneck: Current local outcome evidence for `./tes dev --demo-run` is unavailable.
- Estimated next highest-value work: Outcome-validate `./tes dev --demo-run` and capture dashboard health, generated `run_id`, run detail, replay visibility, and clean shutdown.

## Operations Snapshot

- Throughput: Recent completed work has primarily improved workflow governance and planning quality.
- Capacity: Good for workflow and state maintenance; product validation capacity still depends on local API/dashboard startup evidence.
- Usage observations: Usage unavailable.
- Efficiency note: Planning and workflow structure are now mature enough that the next highest-value work should produce validation evidence unless the user explicitly requests more workflow governance.

## Completed Capabilities

- Level 2 Outcome Validation workflow documentation.
- Level 3 Project Operating Loop state files and maintenance rules.
- Level 3 Objective-Driven Planning docs and objective model.
- Project Operations and Capacity Tracking framework.
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
- Before capacity, usage, throughput, or recommendation-value claims, read `OPERATIONS.md`.
- After every completed task, update `OBJECTIVES.md` when progress changes, update operations observations when evidence changes, then update `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.
- Recommended next tasks must include Impact, Risk, Dependencies, Lane, validation target, and operations rationale.
- Prefer unblockers, shared infrastructure, user-visible functionality, validation, automation, then documentation.
- Avoid duplicate tasks, completed work, low-value busywork, workflow churn, documentation-only loops, and documentation before functionality unless the objective is workflow governance.
- Do not commit or push unless the user explicitly approves that action for the specific task.
