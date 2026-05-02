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

### 3) Configure and build C++ engine (Linux/macOS shell)
```bash
./scripts/build_engine.sh
```

### 3) Configure and build C++ components (placeholder)
```powershell
cmake -S . -B build -G "Ninja"
cmake --build build --config Release
```

### 3b) Configure and build with CMake presets (cross-platform)
```bash
# Engine-only build (default, no Python bindings)
cmake --preset debug-ninja
cmake --build --preset debug-ninja
ctest --preset debug-ninja

# Windows Visual Studio / MSVC (Visual Studio 2026, generator "Visual Studio 18 2026")
cmake --preset debug-msvc
cmake --build --preset debug-msvc --config Debug
ctest --test-dir out/build/debug-msvc -C Debug --output-on-failure

# Python bindings build (optional path)
python3 -m pip install --user pybind11
cmake --preset debug-ninja-python
cmake --build --preset debug-ninja-python

# Windows Visual Studio / MSVC + Python bindings
py -3.11 -m pip install --user pybind11
cmake --preset debug-msvc-python
cmake --build --preset debug-msvc-python --config Debug

# Prefer the active shell Python when multiple Python versions are installed
cmake --preset debug-msvc-python ^
  -DPython3_EXECUTABLE="$(Get-Command python).Source" ^
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)"

# Or use the helper script
./scripts/configure_python_bindings.ps1 -Preset debug-msvc-python
cmake --build --preset debug-msvc-python --config Debug

# If MSBuild cannot open pythonXY.lib, pass explicit Python/pybind11 paths
cmake --preset debug-msvc-python ^
  -DPython3_EXECUTABLE="C:/Program Files/Python313/python.exe" ^
  -DPython3_INCLUDE_DIR="C:/Program Files/Python313/Include" ^
  -DPython3_LIBRARY="C:/Program Files/Python313/libs/python313.lib" ^
  -Dpybind11_DIR="<pybind11 cmake dir>"
```

When `TES_BUILD_PYTHON_BINDINGS=ON`, CMake discovers `pybind11` in this order:
1. Vendored source at `engine/third_party/pybind11`.
2. Preinstalled `pybind11` package discoverable by `find_package(pybind11 CONFIG ...)`.

If neither is available, configure fails with an explicit installation hint.

### 4) Run tests/checks (placeholder)
```powershell
# pytest -q
# ctest --test-dir build --output-on-failure
```
