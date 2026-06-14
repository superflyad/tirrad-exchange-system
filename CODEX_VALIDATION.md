# Codex Validation

This document defines validation expectations for Codex work on TES. Validation is now Level 2: outcome validation. Tests and builds are required gates, but they are not the definition of done.

## Required Commands

Use the commands that match the approved task scope:

```bash
./tes check
./tes check python
./tes check python-release
cd web && npm run build
```

## Selection Rules

- Broad repository, engine, integration, or cross-layer changes: run `./tes check`.
- Python-only changes: run at least `./tes check python-release`.
- Web changes: run `cd web && npm run build`.
- Docs-only workflow changes: full build is optional; at minimum, run `git status` and `git diff --stat` when requested.

## Test-Fix-Retest Rules

- Reproduce the failure before changing code when practical.
- Fix only failures connected to the approved task.
- Re-run the relevant command after each fix.
- Add tests for new behavior.
- Add rejection tests when modifying validators or parsers.
- Do not weaken strictness to make tests pass.
- Do not claim success for commands that were not run.

## Level 2 Outcome Validation

Codex must not stop merely because code compiles, tests pass, or services start. Those results are necessary evidence, not completion.

For every task, validate the requested user workflow through the task's mandatory `Success Scenario`.

The required loop is:

1. Implement.
2. Run tests.
3. Execute user workflow.
4. Observe failures.
5. Repair failures.
6. Retest.
7. Repeat until the success scenario succeeds.

The loop ends only when:
- The requested user workflow succeeds.
- Or a documented blocker prevents completion.

## Success Scenario Validation

Each task must include a `Success Scenario` section. Codex must execute the listed steps after implementation and test validation whenever the environment allows it.

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

Completion requires every step to succeed. If a step cannot be executed, Codex must document the blocker and stop only after explaining what is needed to complete the scenario.

## Blocker Rules

Report a blocker when the success scenario cannot be completed because of a prerequisite Codex cannot satisfy within the approved scope.

Examples:
- Missing credentials.
- External service unavailable.
- Missing dependency.
- Insufficient permissions.
- Required local data, fixture, or configuration unavailable.
- Network or browser capability unavailable for a required check.

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
- `./tes check`: passed / failed / not run
- `./tes check python`: passed / failed / not run
- `./tes check python-release`: passed / failed / not run
- `cd web && npm run build`: passed / failed / not run
```

Only mark a command as passed when it was actually run and exited successfully.

## Required Completion Report Success Scenario Section

Use this format for Level 2 tasks:

```markdown
## SUCCESS SCENARIO

Steps executed:

Observed result:

Evidence:

Remaining issues:

Blockers:

Recommended next task:
```

The `Evidence` field should cite concrete outputs such as command results, file paths, logs, screenshots, generated artifacts, or observed UI state.
