# TES Engine Build & Test (Windows + MSVC)

This directory contains a minimal C++20 CMake scaffold for the TES engine static library and unit tests.

## Prerequisites

- Windows with **Visual Studio Build Tools** (Desktop development with C++) or full Visual Studio with C++ workload.
- `cmake` available on `PATH`.
- PowerShell.

## Build and run tests

From the repository root, run:

```powershell
.\engine\build.ps1
```

The script performs exactly:

```powershell
cmake -S engine -B engine/build
cmake --build engine/build --config Debug
```

Then it automatically runs the test executable from the correct location (e.g. `engine/build/Debug/tes_engine_tests.exe` for MSVC multi-config generators).

## Troubleshooting

- **"cmake is not recognized"**
  - Install CMake and ensure it is on your `PATH`.
- **MSVC compiler not found / CMAKE_CXX_COMPILER errors**
  - Install Visual Studio Build Tools with C++ workload.
  - Run from a Developer PowerShell prompt if toolchain environment is not auto-detected.
- **Test binary not found**
  - Ensure build completed successfully.
  - Re-run with `--config Debug` and verify `engine/build/Debug/tes_engine_tests.exe` exists.
