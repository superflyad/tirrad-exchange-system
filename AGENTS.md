# AGENTS.md

## Repository Mission
Tirrad Exchange System (TES) is a deterministic exchange simulation platform for research, strategy development, and repeatable execution analysis. TES prioritizes strict contracts, reproducibility, and stable behavior over ad-hoc convenience.

## Current Architecture
- The C++20 matching engine in `engine/` is the source of truth for matching behavior and execution semantics.
- `engine/python/bindings.cpp` is the Python serialization firewall between engine internals and Python-visible data.
- Python command models validate all simulation and strategy input before execution.
- Python event models validate all engine output consumed by Python.
- The simulation runner executes only strict, validated commands.
- The strategy layer emits only strict, validated commands.
- Analytics and serialization layers operate only on strict, validated events.
- `./tes` is the single command interface for build, test, and workflow entry points.

## Folder Responsibilities
- `engine/`: C++20 matching engine core, order book behavior, and pybind11 bridge implementation.
- `sim/`: Python 3.14+ simulation, strategy, analytics, serialization, and model layers.
- `docs/`: architecture, contributor, and usage documentation.
- `examples/`: runnable examples and reference workflows.
- `out/`: generated outputs and local artifacts.
- `.github/`: CI, automation, and repository policy configuration.

Do not create new top-level folders unless explicitly requested.

## Non-Negotiable Contract Rules
- Python-visible event shape must remain exactly:
  - `{ "type": "...", "data": {...} }`
- Do not leak raw C++ internals into Python-visible outputs.
- Do not expose enum integers, variant indexes, C++ class names, namespaces, debug fields, or other implementation-only fields in public Python output.
- Strategy and simulation code must use strict command and event models.
- Do not weaken parser or validator strictness to make tests pass.
- Do not pass raw dictionaries beyond parser/serialization boundaries when strict models exist.

## C++ Standards
- Use C++20.
- Preserve deterministic behavior in all engine-visible logic.
- Prefer RAII and explicit ownership.
- Prefer the C++ standard library over ad-hoc infrastructure.
- Keep headers narrow and translation units cohesive.
- Avoid hidden global state.
- Do not change matching behavior unless explicitly requested.
- Preserve and maintain engine test coverage for affected behavior.

## Python Standards
- Use Python 3.14+.
- Prefer a stdlib-first approach unless an external dependency is explicitly required.
- Require type hints for public APIs.
- Use frozen dataclasses for strict contract models where appropriate.
- Enforce exact key validation at parser and serialization boundaries.
- Reject `bool` where `int` is required.
- Do not pass raw dictionaries beyond parser/serialization boundaries when strict models exist.
- Keep modules small and cohesive.
- Avoid ambiguous structures.

## Public API Standards
Canonical event serialization API:
- `serialize_event(event)`
- `serialize_events(events)`

Command models:
- `LimitOrderCommand`
- `CancelOrderCommand`
- `TesCommand`

Event models:
- `OrderAcceptedEvent`
- `OrderCanceledEvent`
- `TradeExecutedEvent`
- `TopOfBookEvent`
- `TesEvent`

## Testing Requirements
Preferred validation flow:
- `./tes check`
- `./tes check python`
- `./tes check python-release`

Minimum required for Python-only changes:
- `./tes check python-release`

Testing policy:
- Do not claim tests passed unless they were actually run.
- Keep all tests under `sim/tests` discoverable by the repository test workflow.
- Add tests for every new behavior.
- Add rejection tests when modifying validators or parsers.

## Branch Naming
Do not use `codex/` branch prefixes.

Use one of:
- `feature/<short-kebab-name>`
- `fix/<short-kebab-name>`
- `docs/<short-kebab-name>`
- `test/<short-kebab-name>`
- `refactor/<short-kebab-name>`
- `chore/<short-kebab-name>`

## Commit Messages
Use Conventional Commits:

`<type>(<scope>): <imperative summary>`

Allowed types:
- `feat`
- `fix`
- `docs`
- `test`
- `refactor`
- `chore`
- `build`
- `ci`

Good examples:
- `docs(agents): define TES contributor standards`
- `fix(sim): reject bool for integer quantity fields`
- `test(engine): cover deterministic partial fill ordering`

Bad examples:
- `update stuff`
- `misc fixes`
- `feat: changes`

## Pull Request Standards
PR title format:
`<type>(<scope>): <imperative summary>`

PR body must include these sections:
- Summary
- Testing
- Scope Control
- Contract Safety
- Risk

The Testing section must list only tests actually run.

## Codex Cloud Rules
- Follow requested file scope exactly.
- Do not edit unrelated files.
- Do not add dependencies without explicit approval.
- Do not use `codex/` branch prefixes.
- Do not add a `codex` label.
- Codex-created PRs must not keep the `codex` label; repository automation removes it if added.
- Use Conventional Commits.
- Use requested branch name, commit title, and PR title when provided.
- Stop and report immediately if the task requires files outside the allowed scope.
- For parallel tasks, avoid shared files unless the task explicitly owns them.
- PR bodies must follow `.github/pull_request_template.md`.

## Parallel Task Rules
- Parallel tasks must have disjoint file ownership.
- If shared files are required, assign a single owning task.
- Do not let multiple tasks modify `sim/tes_models`, `sim/tes_engine_adapter.py`, `engine/python/bindings.cpp`, or `tes` at the same time.
- Merge integration tasks last.

## Definition of Done
A change is done only when all are true:
- Relevant tests pass.
- New behavior includes tests.
- Strict command/event contracts remain intact.
- No unrelated files are changed.
- Commit message follows Conventional Commits.
- PR body follows the required standard sections.
- Public APIs are documented or obvious from typed interfaces.
