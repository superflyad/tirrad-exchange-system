# Tirrad Roadmap

This roadmap is a lightweight planning surface for controlled Codex work. It does not replace issues, pull requests, or human approval.

## Active Workflow Level

Level 1: single-task iteration is active now.

Levels 2-4 are documented in `CODEX_WORKFLOW.md` but require human approval before use.

## Near-Term Workflow Tasks

1. Add `./tes dev` as the recommended first Level 1 implementation task after human approval.
2. Define the expected local development startup behavior for engine, simulation, API, and web surfaces.
3. Add validation coverage for any new workflow command behavior.
4. Review whether `NEXT_TASK.md` should be updated after each approved task.

## Operating Principles

- Keep tasks small, scoped, and validation-ready.
- Preserve strict command and event contracts.
- Do not modify matching behavior unless explicitly requested.
- Prefer repository workflow entry points through `./tes`.
- Keep human approval as the gate for commits, pushes, PRs, and merges.
