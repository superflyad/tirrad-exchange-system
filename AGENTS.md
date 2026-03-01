# AGENTS.md

## Repository overview
This repository hosts **tirrad-exchange-system (TES)**, a deterministic exchange simulation stack built around:
- a **C++ matching engine core** for order-book and execution logic,
- a **Python analytics/simulation layer** for scenario generation and evaluation,
- a **dashboard/observability surface** for inspecting runs and baseline comparisons.

The primary goal is reproducible, non-HFT research and analytical workflows.

## Folder responsibilities
As the codebase grows, follow this ownership model and keep responsibilities clear:
- `engine/` — C++20 exchange core (matching engine, order book, risk checks, deterministic replay).
- `python/` — Python 3.11+ orchestration, data prep, analytics, and experiment runners.
- `dashboard/` — UI/backend components for run status, metrics, and trade/event visualization.
- `tests/` — cross-language integration and end-to-end tests.
- `docs/` — architecture decisions, user guides, and developer notes.
- `scripts/` — local automation for setup, lint, build, and test tasks.

If a new file does not clearly fit one of these areas, add/update `docs/` notes explaining placement.

## Coding standards

### C++
- Use **C++20**.
- Favor deterministic behavior (stable iteration/order, explicit clocks/seeds).
- Prefer RAII and standard library facilities over ad-hoc resource management.
- Keep translation units cohesive; avoid overly broad headers.

### Python
- Use **Python 3.11+**.
- Require **type hints** for public functions, methods, and module-level constants where appropriate.
- Prefer `pathlib`, `dataclasses`, and explicit return types in new code.
- Keep notebook-like exploratory logic out of production modules.

## Formatting and linting expectations
- Keep formatting and lint output clean before committing.
- C++: run formatter/linter configured for the repo (e.g., `clang-format`, `clang-tidy`) once available.
- Python: use `ruff format`/`black`-style formatting and `ruff`/`mypy` checks once configured.
- Do not mix broad reformatting with unrelated functional changes in the same commit.

## Build and test commands (Windows PowerShell)
Use repository scripts when present; otherwise, these are expected baseline commands:

```powershell
# Python environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
if (Test-Path requirements.txt) { pip install -r requirements.txt }

# Python checks/tests
if (Get-Command ruff -ErrorAction SilentlyContinue) { ruff check . }
if (Get-Command mypy -ErrorAction SilentlyContinue) { mypy . }
if (Get-Command pytest -ErrorAction SilentlyContinue) { pytest -q }

# C++ configure/build/test (CMake)
cmake -S . -B build -G "Ninja"
cmake --build build --config Release
ctest --test-dir build --output-on-failure
```

## Definition of done
A change is complete only when all are true:
1. Relevant tests pass locally.
2. Developer-facing docs are updated (README/docs/inline comments as needed).
3. Commits are small, focused, and have clear messages.
4. Formatting/lint expectations are satisfied for touched files.
