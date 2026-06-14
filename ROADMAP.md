# Tirrad Roadmap

This roadmap is a lightweight planning surface for controlled Codex work. It does not replace issues, pull requests, or human approval.

## Active Workflow Level

Level 3: Project Operating Loop is active now.

Level 3 keeps outcome validation from Level 2 and adds project state maintenance through `ACTIVE_TASKS.md`, `COMPLETED_TASKS.md`, `NEXT_TASK.md`, and `CODEX_STATE.md`.

## Near-Term Workflow Tasks

1. Implement `./tes dev --demo-run` as the first Level 3 operating-loop task.
2. Define the expected local development startup behavior for engine, simulation, API, and web surfaces.
3. Add validation coverage for any new workflow command behavior.
4. Keep Level 3 state files current after each completed task.

## Operating Principles

- Keep tasks small, scoped, and validation-ready.
- Preserve strict command and event contracts.
- Do not modify matching behavior unless explicitly requested.
- Prefer repository workflow entry points through `./tes`.
- Keep human approval as the gate for commits, pushes, PRs, and merges.
