# Development Notes

## Engine-only bootstrap (Linux/macOS shell)

For early bring-up, build and test only the C++ engine with Python bindings disabled:

```bash
./scripts/build_engine.sh
```

Equivalent CMake preset commands:

```bash
cmake --preset debug-ninja
cmake --build --preset debug-ninja
ctest --preset debug-ninja
```

## Optional Python bindings build

Python bindings are intentionally isolated from the default engine-only build.

### Linux/macOS / Codex

```bash
python3 -m pip install --user pybind11
cmake --preset debug-ninja-python
cmake --build --preset debug-ninja-python
```

### Windows (Visual Studio 2026 / MSVC)

```powershell
py -3.11 -m pip install --user pybind11
cmake --preset release-msvc-python
cmake --build --preset release-msvc-python --config Release
```

When multiple Python versions are installed, make CMake use the same Python as your shell/pip install:

```powershell
cmake --preset release-msvc-python `
  -DPython3_EXECUTABLE="$(Get-Command python).Source" `
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)"
```

Helper script (one command):

```powershell
./scripts/configure_python_bindings.ps1 -Preset release-msvc-python
cmake --build --preset release-msvc-python --config Release
```

If CMake finds Python but MSBuild fails to open `pythonXY.lib`, configure with explicit paths:

```powershell
cmake --preset release-msvc-python `
  -DPython3_EXECUTABLE="C:/Program Files/Python313/python.exe" `
  -DPython3_INCLUDE_DIR="C:/Program Files/Python313/Include" `
  -DPython3_LIBRARY="C:/Program Files/Python313/libs/python313.lib" `
  -Dpybind11_DIR="<pybind11 cmake dir>"
```

Discovery behavior when Python bindings are enabled (`TES_BUILD_PYTHON_BINDINGS=ON`):
- CMake requires `Python3` components `Interpreter` and `Development.Module`.
- CMake prefers vendored `engine/third_party/pybind11` when present.
- Otherwise CMake searches for installed `pybind11` (`find_package(pybind11 CONFIG ...)`).
- If missing, configure fails with install guidance.

Override defaults manually when needed:

```bash
TES_BUILD_PYTHON_BINDINGS=ON ./scripts/build_engine.sh engine/build-py
```

## Why this script exists

- Keeps local/CI bootstrap deterministic and minimal.
- Matches the current verified path for environments without Python binding dependencies.
- Avoids platform-specific command drift between Windows and Unix-like shells.


### TES wrapper commands

```bash
./tes check                # core engine default preset
./tes check python         # python bindings + import smoke test
./tes check python-release # windows release-msvc-python; linux ninja python flow
./tes presets
./tes clean
```

Windows note: use Release for Python binding import checks unless using a debug Python runtime.
