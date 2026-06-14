# Objectives

Level 3 Objective-Driven Planning uses this file as the first planning input. Codex must read `OBJECTIVES.md` before `NEXT_TASK.md`, derive tasks from objective and milestone state, and update progress when validation evidence changes.

## Objective Model

Each objective must contain:

- Title
- Description
- Success Criteria
- Milestones
- Current Status
- Progress %
- Completed Milestones
- Remaining Milestones
- Current Bottleneck
- Estimated Next Highest-Value Work
- Known Risks
- Dependencies

Objective status values:
- Not Started
- Active
- Blocked
- Complete

Progress should be evidence-based and milestone-weighted unless an objective defines a more precise metric.

Each objective may include an `Operations Tracking` block with throughput, capacity, blocker, and usage observations. Do not invent usage values. Use `Usage unavailable` when usage is not available.

## Milestone Model

Each milestone must contain:

- Name
- Description
- Status: Not Started / Active / Blocked / Complete
- Related Tasks
- Validation Criteria

## Work Lanes

- Core/API
- Dashboard/UI
- Dev Workflow
- Tests/Documentation

## Active Objectives

### One-command local onboarding

- Description: A fresh local checkout should be able to start TES, create a demo run, show a healthy dashboard, and expose replay data through one repository workflow command without manual fixes.
- Current Status: Active
- Progress %: 35
- Completed Milestones:
  - Root `./tes` workflow entry point exists.
  - API demo-run helper exists.
  - Dashboard run, live monitor, and replay surfaces are present.
- Remaining Milestones:
  - Python verification
  - Current unified local startup outcome evidence
  - Dashboard run and replay visibility evidence
  - Automated smoke validation
- Current Bottleneck: Current recorded local outcome evidence for `./tes dev --demo-run` is unavailable.
- Estimated Next Highest-Value Work: Outcome-validate `./tes dev --demo-run` and record dashboard health, generated `run_id`, run detail, replay visibility, and clean shutdown evidence.
- Dependencies:
  - Root `./tes` workflow entry point
  - Local Python/API environment
  - Dashboard build and runtime
  - Persisted demo run data
  - Replay route availability
- Known Risks:
  - Existing `./tes dev --demo-run` behavior has not been outcome-validated on this machine in the current state record.
  - Dashboard run and replay visibility may depend on local ports, generated run IDs, or persisted storage state.
  - Automated smoke validation may require stable startup and shutdown semantics.

#### Success Criteria

```text
Fresh clone
-> ./tes dev --demo-run
-> Dashboard healthy
-> Replay visible
-> No manual fixes
```

#### Milestones

##### Build verification

- Description: Repository-level build and launcher checks are available and can be run through `./tes`.
- Status: Active
- Related Tasks:
  - Outcome-validate `./tes dev --demo-run`
  - Run launcher-focused validation before end-to-end workflow checks
- Validation Criteria:
  - `./tes` workflow entry point is present.
  - Relevant launcher or repository checks pass when selected for the task.
  - No product code changes are needed for workflow documentation tasks.

##### Python verification

- Description: Python simulation, API, persistence, and replay surfaces required by the demo path validate through the selected Python check.
- Status: Not Started
- Related Tasks:
  - Run `./tes check python-release` when the onboarding workflow task requires Python validation.
  - Record any Python validation blocker as objective evidence.
- Validation Criteria:
  - Selected Python validation passes, or a blocker is documented.
  - Strict command and event contracts remain intact.

##### Unified local startup

- Description: `./tes dev --demo-run` starts the required local services and prints enough information for the user to inspect the dashboard and replay.
- Status: Active
- Related Tasks:
  - Execute `./tes dev --demo-run`.
  - Capture dashboard health and printed run information.
- Validation Criteria:
  - Command starts the local API and dashboard.
  - Dashboard health reports OK.
  - Command prints a non-empty `run_id`.
  - Services shut down cleanly after validation.

##### Outcome validation

- Description: The generated demo run is visible through the dashboard and replay workflow.
- Status: Not Started
- Related Tasks:
  - Verify generated run appears in the dashboard or API run list.
  - Verify run detail loads for the printed `run_id`.
  - Verify replay page loads for the printed `run_id`.
- Validation Criteria:
  - Generated run is visible.
  - Run detail is visible.
  - Replay data is visible.
  - No manual fix is required.

##### Automated smoke validation

- Description: Convert the proven local onboarding workflow into repeatable smoke validation.
- Status: Not Started
- Related Tasks:
  - Define smoke coverage after manual outcome validation succeeds.
  - Add automation only after stable startup, dashboard health, and replay visibility are proven.
- Validation Criteria:
  - Automated smoke command exercises startup, health, run creation, replay visibility, and clean shutdown.
  - Smoke validation is reachable through `./tes`.
  - Documentation explains how to run the smoke path after functionality is proven.

#### Operations Tracking

- Progress %: 35
- Completed milestones:
  - Root `./tes` workflow entry point exists.
  - API demo-run helper exists.
  - Dashboard run, live monitor, and replay surfaces are present.
- Remaining milestones:
  - Python verification
  - Unified local startup outcome evidence
  - Outcome validation through dashboard run detail and replay visibility
  - Automated smoke validation
- Current bottleneck: Current local outcome evidence for `./tes dev --demo-run` is unavailable.
- Estimated next highest-value work: Outcome-validate `./tes dev --demo-run` and capture dashboard health, generated `run_id`, run detail, replay visibility, and clean shutdown.
- Throughput notes: Level 3 planning and operations framework work is complete enough; the next highest-value work should produce validation evidence.
- Capacity notes: Local validation capacity depends on API/dashboard startup and port availability.
- Usage observations: Usage unavailable.

## Candidate Task Ranking Rules

When deriving work from this file, Codex should rank candidate tasks by project impact:

1. Unblockers
2. Infrastructure required by multiple milestones
3. User-visible functionality
4. Validation
5. Automation
6. Documentation

Avoid duplicate tasks, completed work, low-value busywork, workflow churn, documentation-only loops, and documentation before functionality unless the active objective is itself workflow governance.

## Recommended First Objective

The recommended first objective for TES is `One-command local onboarding` because it proves the core local operator workflow across repository commands, API startup, dashboard health, persisted runs, and replay visibility.
