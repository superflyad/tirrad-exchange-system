# Codex Validation

This document defines validation expectations for Codex work on TES.

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

## Stop Conditions

Stop and ask the user when:
- A fix requires files outside the approved scope.
- A fix requires product behavior changes not requested by the task.
- Matching behavior would change without explicit approval.
- A dependency would need to be added.
- Validation failures appear unrelated to the task.
- The repository instructions conflict with the requested action.

## Completion Report Validation Section

Use this format:

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
