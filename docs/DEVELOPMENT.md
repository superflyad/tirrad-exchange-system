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
cmake --preset debug-msvc-python
cmake --build --preset debug-msvc-python --config Debug
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
