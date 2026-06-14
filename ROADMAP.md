# Tirrad Roadmap

This roadmap is a lightweight planning surface for controlled Codex work. It does not replace issues, pull requests, or human approval.

## Active Workflow Level

Level 3: Project Operating Loop is active now.

Level 3 keeps outcome validation from Level 2 and adds project state maintenance through `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.

## Near-Term Workflow Tasks

1. Outcome-validate the existing `./tes dev --demo-run` workflow from command startup through dashboard run/replay inspection.
2. Close any validation gaps found in the local development startup behavior for API, dashboard, persisted run creation, and replay surfaces.
3. Document contributor-facing Level 3 usage only after the executable workflow has current outcome evidence.
4. Keep Level 3 state files current after each completed task.

## Operating Principles

- Keep tasks small, scoped, and validation-ready.
- Preserve strict command and event contracts.
- Do not modify matching behavior unless explicitly requested.
- Prefer repository workflow entry points through `./tes`.
- Keep human approval as the gate for commits, pushes, PRs, and merges.
