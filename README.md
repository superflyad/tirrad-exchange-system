# tirrad-exchange-system

TES (tirrad-exchange-system) is a deterministic exchange simulation project that pairs a C++ matching-engine core with Python-based simulation and analytics workflows plus observability tooling for run and trade inspection. The project is focused on reproducible market-structure analysis and strategy evaluation in a **non-HFT analytical context**, prioritizing explainability, repeatability, and baseline comparison over ultra-low-latency production concerns.

## Repository Layout

```
engine/   C++ matching engine core
sim/      Python simulation + analytics orchestration
api/      service/API boundary for run control and data access
web/      dashboard and observability UI/backend
scripts/  developer automation
docs/     architecture and developer notes
tests/    cross-module integration tests
runs/     local run artifacts (gitkept, ignored contents)
data/     local datasets/cache (gitkept, ignored contents)
```

## Local Dev Quickstart

> Placeholder quickstart commands (update as the project structure is finalized).

### 1) Clone and enter the repository
```powershell
git clone <repo-url>
cd tirrad-exchange-system
```

### 2) Set up Python environment (placeholder)
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
# pip install -r requirements.txt
```

### 3) Configure and build C++ components (placeholder)
```powershell
cmake -S . -B build -G "Ninja"
cmake --build build --config Release
```

### 4) Run tests/checks (placeholder)
```powershell
# pytest -q
# ctest --test-dir build --output-on-failure
```
