# Next Task

## Recommended Level 2 Implementation Task

Implement `./tes dev --demo-run` as the first outcome-validated workflow.

## Goal

Create a deterministic demo-run workflow that can be validated from command start through observable user outcome, proving the new Level 2 workflow standard in practice.

## Suggested Scope

- Inspect the existing `tes` workflow script.
- Define the intended `./tes dev --demo-run` behavior before implementation.
- Keep the implementation limited to the approved workflow command and supporting tests or documentation.
- Do not change engine matching behavior, public API contracts, dashboard behavior, or strict command/event models unless explicitly approved.
- Add or update tests for the workflow command where practical.
- Update documentation for the command.

## Success Scenario

1. Start stack.
2. Open dashboard.
3. Verify health page.
4. Generate run.
5. Verify run appears.
6. Verify replay data loads.
7. Shut down cleanly.

The task is incomplete until all steps succeed or a blocker is documented with evidence.

## Validation

- `./tes check`
- `./tes check python`
- `./tes check python-release`
- `cd web && npm run build`

Run only the commands that match the approved implementation scope, then execute the success scenario. Report exactly what was run and what was observed.

## Completion Report

The completion report must include:
- Files changed.
- Validation commands run and results.
- SUCCESS SCENARIO.
- Evidence for each completed scenario step.
- Remaining issues.
- Blockers.
- Recommended next task.

## Permissions

- Do not commit without explicit user approval.
- Do not push without explicit user approval.
- Stop after the completion report unless the user asks for the next action.
