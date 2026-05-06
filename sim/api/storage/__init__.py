"""Storage backend selection for the TES API service."""

from __future__ import annotations

import os
from pathlib import Path

from sim.api.storage.base import RunRecord, RunStore, TournamentRecord
from sim.api.storage.in_memory import InMemoryRunStore
from sim.api.storage.sqlite import SQLiteRunStore

DEFAULT_SQLITE_PATH = Path("runs/tes_runs.sqlite")


def create_run_store(*, store: str | None = None, sqlite_path: str | Path | None = None) -> RunStore:
    """Create the configured API run store.

    ``TES_RUN_STORE`` accepts ``memory`` or ``sqlite``. ``TES_SQLITE_PATH`` sets
    the SQLite database path when SQLite is selected.
    """

    selected = (store or os.environ.get("TES_RUN_STORE") or "sqlite").strip().lower()
    if selected == "memory":
        return InMemoryRunStore()
    if selected == "sqlite":
        path = sqlite_path or os.environ.get("TES_SQLITE_PATH") or DEFAULT_SQLITE_PATH
        return SQLiteRunStore(path)
    raise ValueError("TES_RUN_STORE must be 'memory' or 'sqlite'")


__all__ = [
    "DEFAULT_SQLITE_PATH",
    "InMemoryRunStore",
    "RunRecord",
    "TournamentRecord",
    "RunStore",
    "SQLiteRunStore",
    "create_run_store",
]
