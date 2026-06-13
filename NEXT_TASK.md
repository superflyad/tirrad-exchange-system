# Next Task

## Recommended Level 1 Task

Add `./tes dev` as a repository workflow command.

## Goal

Define and implement a deterministic local development entry point that helps contributors start the appropriate TES development surfaces through `./tes` without changing product behavior unexpectedly.

## Suggested Scope

- Inspect the existing `tes` workflow script.
- Define what `./tes dev` should start or report on Windows, Git Bash, and Visual Studio-oriented local setups.
- Implement only the approved command behavior.
- Add or update tests or checks for the workflow command if practical.
- Update documentation for the new command.

## Validation

- `./tes check`
- `./tes check python`
- `./tes check python-release`
- `cd web && npm run build`

Run only the commands that match the approved implementation scope, and report exactly what was run.

## Permissions

- Do not commit without explicit user approval.
- Do not push without explicit user approval.
- Stop after the completion report unless the user asks for the next action.
