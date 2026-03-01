# tes_engine Python bindings

This folder contains a `pybind11` extension module that exposes the C++ matching engine as `tes_engine`.

## Exposed API

```python
import tes_engine

engine = tes_engine.MatchingEngine()
engine.place_limit_order(side="Ask", price_ticks=100, qty=10)
engine.cancel(order_id=1)
```

Both methods return `list[dict]` events. The dictionaries include a `type` field (`OrderAccepted`, `OrderCanceled`, `TradeExecuted`, or `TopOfBook`) plus event-specific fields.

## Windows build steps (PowerShell)

From repository root:

```powershell
# 1) Create and activate Python virtual environment
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip

# 2) Configure CMake and point it at the venv Python executable
cmake -S engine -B build/engine -G "Ninja" `
  -DPython3_EXECUTABLE="$PWD/.venv/Scripts/python.exe" `
  -DTES_BUILD_PYTHON_BINDINGS=ON

# 3) Build tests + Python extension
cmake --build build/engine --config Release

# 4) Make module importable in current shell
$env:PYTHONPATH = "$PWD/build/engine/Release;$PWD/build/engine"

# 5) Smoke check
python -c "import tes_engine; print(tes_engine.MatchingEngine())"
```

## Notes

- The CMake logic prefers vendored `engine/third_party/pybind11` if present.
- If vendored pybind11 is absent, CMake falls back to a preinstalled `pybind11` package (`find_package(pybind11 CONFIG)`).
- The build is network-free by default (no `FetchContent`).
