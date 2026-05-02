# Contributing to Tirrad Exchange System (TES)

## Start with AGENTS.md
Read `AGENTS.md` before making changes. It is the source of truth for repository contracts, architecture boundaries, and contributor behavior.

## Branch Naming
Create branches using one of these prefixes:
- `feature/<short-kebab-name>`
- `fix/<short-kebab-name>`
- `docs/<short-kebab-name>`
- `test/<short-kebab-name>`
- `refactor/<short-kebab-name>`
- `chore/<short-kebab-name>`

Do not use the `codex/` prefix.

Do not add the `codex` label manually.

Codex connector labels may be removed manually.

## Commit Format
Use Conventional Commits:

`<type>(<scope>): <imperative summary>`

Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`, `ci`.

## Pull Request Requirements
- Use the repository PR template in `.github/pull_request_template.md`.
- PR title must follow Conventional Commit format.
- PR body must include: Summary, Testing, Scope Control, Contract Safety, Risk.
- List only tests actually run in the Testing section.
- Keep scope strict and avoid unrelated edits.

## Required Test Commands
Preferred validation flow:
- `./tes check`
- `./tes check python`
- `./tes check python-release`

Minimum for Python-only changes:
- `./tes check python-release`

Do not claim tests passed unless they were actually run.

## TES Architecture Layers
- `engine/`: C++20 matching engine; source of truth for matching behavior.
- `engine/python/bindings.cpp`: serialization firewall between C++ internals and Python-visible outputs.
- `sim/`: Python 3.14+ simulation and strategy layers with strict command/event validation.
- Python-visible event shape is fixed: `{ "type": "...", "data": {...} }`.
- Do not leak C++ internals into Python contracts.
