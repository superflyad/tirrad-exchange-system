#!/usr/bin/env bash
set -euo pipefail

# Cross-platform-friendly engine build helper for Linux/macOS shells.
# Python bindings are disabled by default to keep bootstrap requirements minimal.

BUILD_DIR="${1:-engine/build}"
GENERATOR="${CMAKE_GENERATOR:-Ninja}"
BINDINGS="${TES_BUILD_PYTHON_BINDINGS:-OFF}"

cmake -S engine -B "${BUILD_DIR}" -G "${GENERATOR}" -DTES_BUILD_PYTHON_BINDINGS="${BINDINGS}"
cmake --build "${BUILD_DIR}"
ctest --test-dir "${BUILD_DIR}" --output-on-failure
