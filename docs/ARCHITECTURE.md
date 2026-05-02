# TES Architecture

## Product posture and operating model

TES (tirrad-exchange-system) is a deterministic, analytics-first exchange simulation platform.
It is intentionally **non-HFT**: correctness, repeatability, and explainability are valued over ultra-low-latency concerns.

Core operating rule: for the same initial state, command stream, and seeds, TES must emit the same ordered event stream.

## Layered architecture (Tasks 7–10 baseline)

### 1) C++ engine = behavior source of truth

The `engine/` C++ core is the authoritative implementation of exchange behavior:
- order lifecycle transitions,
- matching/execution semantics,
- rejection and risk outcomes,
- deterministic event ordering.

Any downstream component (Python simulation, analytics, APIs, dashboard) must treat engine outputs as canonical behavior.

### 2) `bindings.cpp` = serialization firewall

`engine/python/bindings.cpp` is the narrow boundary between C++ domain internals and Python consumers.
Its responsibilities are deliberately constrained:
- expose stable Python-facing types/contracts,
- serialize/deserialize commands/events across the boundary,
- prevent leakage of C++-internal representations into Python orchestration code.

This “serialization firewall” keeps evolution of engine internals decoupled from Python-side workflow logic.

### 3) Strict Python event models

Python event models are strict by design:
- explicit typed fields,
- validation of required attributes,
- deterministic parse/normalization behavior,
- rejection of ambiguous/unknown shapes.

This ensures that event consumers (simulation, analytics, tests) operate on one validated schema rather than ad-hoc dictionaries.

### 4) Strict Python command models

Python command models mirror the same strictness for engine inputs:
- explicit command types and payload fields,
- validation before crossing the binding boundary,
- deterministic command serialization order.

Result: command intent is validated early, and invalid requests fail fast before engine invocation.

### 5) Engine adapter

The engine adapter provides a stable orchestration interface over the raw binding surface.
It centralizes:
- command submission,
- event stream retrieval,
- error normalization,
- deterministic run setup.

This isolates higher-level simulation code from binding-level implementation detail.

### 6) Simulation runner

The simulation runner is the execution coordinator for deterministic experiments:
- initializes run context,
- sequences command generation/submission,
- captures emitted events,
- manages run artifacts and outcome summaries.

It acts as the bridge between strategies and the engine adapter.

### 7) Strategy interface

The strategy interface defines how pluggable strategy modules participate in a run:
- consume normalized market/run state,
- produce strict command-model outputs,
- run in deterministic step order,
- remain decoupled from engine internals.

This enables comparable strategy experiments using a shared execution substrate.

### 8) Parallel Codex task workflow

Documentation and implementation work is structured for parallel Codex-friendly delivery:
- bounded tasks with explicit acceptance criteria,
- contract-first updates at architecture boundaries,
- additive, reviewable commits,
- integration checks run via `./tes check` flows.

This workflow reduces merge conflicts and preserves deterministic behavior guarantees while multiple tasks progress concurrently.

## Validation commands (verified)

The following project checks are part of the current architecture validation workflow:

```bash
./tes check
./tes check python
./tes check python-release
```

## Roadmap (Tasks 11–15)

- **Task 11:** strategy simulation loop completion and hardening.
- **Task 12:** analytics layer expansion (metrics, comparative reports, scenario outputs).
- **Task 13:** persistence layer for run/event/summary artifacts.
- **Task 14:** API/service boundary for run control and data retrieval.
- **Task 15:** dashboard experience for observability and analysis workflows.
