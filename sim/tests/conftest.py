"""Shared pytest setup for TES simulation tests."""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    build_engine_dir = Path(__file__).resolve().parents[2] / "out" / "build" / "debug-ninja-python" / "engine"
    if build_engine_dir.exists():
        sys.path.insert(0, str(build_engine_dir))
