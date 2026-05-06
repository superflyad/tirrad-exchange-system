"""SQLite-backed durable run queue for TES API execution."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

QueueStatus = Literal["pending", "running", "completed", "failed", "canceled"]


@dataclass(frozen=True)
class QueueItem:
    """Durable queue row claimed or observed by workers."""

    run_id: str
    status: QueueStatus
    priority: int
    created_at: datetime
    available_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    attempts: int
    last_error: str | None
    locked_by: str | None
    locked_at: datetime | None


@dataclass(frozen=True)
class WorkerHeartbeat:
    """Observable worker liveness record."""

    worker_id: str
    status: str
    updated_at: datetime
    current_run_id: str | None


class SQLiteRunQueue:
    """Durable SQLite queue with atomic run claiming semantics."""

    def __init__(self, path: str | Path, *, timeout: float = 5.0, stale_after_seconds: int = 900) -> None:
        self.path = Path(path)
        database = ":memory:" if self.path == Path(":memory:") else str(self.path)
        if database != ":memory:":
            self.path.expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._stale_after_seconds = stale_after_seconds
        self._connection = sqlite3.connect(database, timeout=timeout, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._configure_connection()
        self._initialize_schema()

    def enqueue(self, run_id: str, *, priority: int = 0, available_at: datetime | None = None) -> QueueItem:
        now = datetime.now(UTC)
        available = available_at or now
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO run_queue (
                    run_id, status, priority, created_at, available_at, started_at,
                    completed_at, attempts, last_error, locked_by, locked_at
                ) VALUES (?, 'pending', ?, ?, ?, NULL, NULL, 0, NULL, NULL, NULL)
                ON CONFLICT(run_id) DO UPDATE SET
                    status = CASE
                        WHEN run_queue.status IN ('completed', 'running') THEN run_queue.status
                        ELSE 'pending'
                    END,
                    priority = excluded.priority,
                    available_at = excluded.available_at,
                    completed_at = NULL,
                    last_error = NULL,
                    locked_by = NULL,
                    locked_at = NULL
                """,
                (run_id, priority, _format_datetime(now), _format_datetime(available)),
            )
        item = self.get(run_id)
        if item is None:
            raise RuntimeError(f"failed to enqueue run: {run_id}")
        return item

    def dequeue(self, *, worker_id: str = "worker") -> QueueItem | None:
        return self.claim_next(worker_id)

    def claim_next(self, worker_id: str) -> QueueItem | None:
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=self._stale_after_seconds)
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE run_queue
                SET status = 'running', started_at = COALESCE(started_at, ?), attempts = attempts + 1,
                    locked_by = ?, locked_at = ?, last_error = NULL
                WHERE run_id = (
                    SELECT run_id FROM run_queue
                    WHERE (
                        status = 'pending'
                        OR (status = 'running' AND locked_at IS NOT NULL AND locked_at < ?)
                    )
                    AND available_at <= ?
                    ORDER BY priority DESC, created_at ASC, run_id ASC
                    LIMIT 1
                )
                RETURNING *
                """,
                (
                    _format_datetime(now),
                    worker_id,
                    _format_datetime(now),
                    _format_datetime(stale_before),
                    _format_datetime(now),
                ),
            )
            row = cursor.fetchone()
        return _item_from_row(row) if row is not None else None

    def mark_running(self, run_id: str, *, worker_id: str | None = None) -> QueueItem | None:
        now = datetime.now(UTC)
        with self._connection:
            self._connection.execute(
                """
                UPDATE run_queue
                SET status = 'running', started_at = COALESCE(started_at, ?),
                    locked_by = COALESCE(?, locked_by), locked_at = ?
                WHERE run_id = ? AND status != 'completed'
                """,
                (_format_datetime(now), worker_id, _format_datetime(now), run_id),
            )
        return self.get(run_id)

    def mark_completed(self, run_id: str) -> QueueItem | None:
        return self._mark_terminal(run_id, "completed", None)

    def mark_failed(self, run_id: str, error: str) -> QueueItem | None:
        return self._mark_terminal(run_id, "failed", error)

    def mark_canceled(self, run_id: str, error: str | None = None) -> QueueItem | None:
        return self._mark_terminal(run_id, "canceled", error)

    def cancel_pending(self, run_id: str) -> bool:
        now = datetime.now(UTC)
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE run_queue
                SET status = 'canceled', completed_at = ?, locked_by = NULL, locked_at = NULL,
                    last_error = COALESCE(last_error, 'canceled before execution')
                WHERE run_id = ? AND status = 'pending'
                """,
                (_format_datetime(now), run_id),
            )
        return cursor.rowcount > 0

    def heartbeat(self, worker_id: str, *, status: str = "idle", current_run_id: str | None = None) -> None:
        now = datetime.now(UTC)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO worker_heartbeats (worker_id, status, updated_at, current_run_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    current_run_id = excluded.current_run_id
                """,
                (worker_id, status, _format_datetime(now), current_run_id),
            )

    def list_workers(self) -> list[WorkerHeartbeat]:
        rows = self._connection.execute(
            "SELECT * FROM worker_heartbeats ORDER BY updated_at DESC, worker_id ASC"
        ).fetchall()
        return [
            WorkerHeartbeat(
                worker_id=row["worker_id"],
                status=row["status"],
                updated_at=_parse_datetime(row["updated_at"]),
                current_run_id=row["current_run_id"],
            )
            for row in rows
        ]

    def list_pending(self) -> list[QueueItem]:
        return self._list_by_status("pending")

    def list_running(self) -> list[QueueItem]:
        return self._list_by_status("running")

    def get(self, run_id: str) -> QueueItem | None:
        row = self._connection.execute("SELECT * FROM run_queue WHERE run_id = ?", (run_id,)).fetchone()
        return _item_from_row(row) if row is not None else None

    def close(self) -> None:
        self._connection.close()

    def _mark_terminal(self, run_id: str, status: QueueStatus, error: str | None) -> QueueItem | None:
        now = datetime.now(UTC)
        with self._connection:
            self._connection.execute(
                """
                UPDATE run_queue
                SET status = ?, completed_at = ?, last_error = ?, locked_by = NULL, locked_at = NULL
                WHERE run_id = ? AND status != 'completed'
                """,
                (status, _format_datetime(now), error, run_id),
            )
        return self.get(run_id)

    def _list_by_status(self, status: QueueStatus) -> list[QueueItem]:
        rows = self._connection.execute(
            "SELECT * FROM run_queue WHERE status = ? ORDER BY priority DESC, created_at ASC, run_id ASC",
            (status,),
        ).fetchall()
        return [_item_from_row(row) for row in rows]

    def _configure_connection(self) -> None:
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        if self.path != Path(":memory:"):
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = NORMAL")

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS run_queue (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                available_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                locked_by TEXT,
                locked_at TEXT
            );

            CREATE TABLE IF NOT EXISTS worker_heartbeats (
                worker_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                current_run_id TEXT
            );

            CREATE TABLE IF NOT EXISTS run_locks (
                run_id TEXT PRIMARY KEY,
                worker_id TEXT NOT NULL,
                locked_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_run_queue_claim
                ON run_queue(status, available_at, priority, created_at);
            CREATE INDEX IF NOT EXISTS idx_run_queue_locked_at ON run_queue(status, locked_at);
            """
        )
        self._connection.commit()


def _item_from_row(row: sqlite3.Row) -> QueueItem:
    return QueueItem(
        run_id=row["run_id"],
        status=row["status"],
        priority=int(row["priority"]),
        created_at=_parse_datetime(row["created_at"]),
        available_at=_parse_datetime(row["available_at"]),
        started_at=_parse_optional_datetime(row["started_at"]),
        completed_at=_parse_optional_datetime(row["completed_at"]),
        attempts=int(row["attempts"]),
        last_error=row["last_error"],
        locked_by=row["locked_by"],
        locked_at=_parse_optional_datetime(row["locked_at"]),
    )


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def _parse_optional_datetime(value: str | None) -> datetime | None:
    return _parse_datetime(value) if value is not None else None
