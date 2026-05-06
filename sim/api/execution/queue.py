"""SQLite-backed durable run queue for TES API execution."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

QueueStatus = Literal["pending", "running", "completed", "failed", "canceled"]
WorkerStatus = Literal["idle", "busy", "offline", "stale"]


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
    status: WorkerStatus | str
    updated_at: datetime
    current_run_id: str | None


@dataclass(frozen=True)
class WorkerRecord:
    """Persistent distributed worker registration record."""

    worker_id: str
    hostname: str
    process_id: int | None
    started_at: datetime
    heartbeat_at: datetime
    capabilities: dict[str, Any] = field(default_factory=dict)
    status: WorkerStatus | str = "idle"
    current_run_id: str | None = None
    progress_summary: dict[str, Any] = field(default_factory=dict)
    cpu_percent: float | None = None
    memory_bytes: int | None = None
    drain_requested: bool = False
    shutdown_requested: bool = False


@dataclass(frozen=True)
class RunLease:
    """Single-owner execution lease for a run."""

    run_id: str
    worker_id: str
    acquired_at: datetime
    expires_at: datetime
    heartbeat_at: datetime


@dataclass(frozen=True)
class SchedulerStatus:
    """Snapshot of scheduler-visible queue, worker, and throughput health."""

    pending_count: int
    running_count: int
    completed_count: int
    failed_count: int
    stale_worker_count: int
    stale_job_count: int
    queue_depth: int
    average_wait_seconds: float
    average_run_seconds: float
    worker_utilization: float
    throughput_per_minute: float


@dataclass(frozen=True)
class RequeueResult:
    """Summary of stale recovery work performed by the scheduler."""

    stale_workers: int
    requeued_runs: list[str]


class SQLiteRunQueue:
    """Durable SQLite queue with atomic run claiming and worker lease semantics."""

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
        expires_at = now + timedelta(seconds=self._stale_after_seconds)
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
            if row is None:
                return None
            self._connection.execute("DELETE FROM run_leases WHERE run_id = ?", (row["run_id"],))
            self._connection.execute(
                """
                INSERT INTO run_leases (run_id, worker_id, acquired_at, expires_at, heartbeat_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (row["run_id"], worker_id, _format_datetime(now), _format_datetime(expires_at), _format_datetime(now)),
            )
        return _item_from_row(row)

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
            if worker_id is not None:
                self._upsert_lease(run_id=run_id, worker_id=worker_id, now=now)
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
            self._connection.execute("DELETE FROM run_leases WHERE run_id = ?", (run_id,))
        return cursor.rowcount > 0

    def register_worker(
        self,
        worker_id: str,
        *,
        hostname: str,
        process_id: int | None = None,
        started_at: datetime | None = None,
        capabilities: dict[str, Any] | None = None,
        status: WorkerStatus | str = "idle",
    ) -> WorkerRecord:
        now = datetime.now(UTC)
        started = started_at or now
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO workers (
                    worker_id, hostname, process_id, started_at, heartbeat_at, capabilities, status,
                    current_run_id, progress_summary, cpu_percent, memory_bytes, drain_requested, shutdown_requested
                ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, '{}', NULL, NULL, 0, 0)
                ON CONFLICT(worker_id) DO UPDATE SET
                    hostname = excluded.hostname,
                    process_id = excluded.process_id,
                    heartbeat_at = excluded.heartbeat_at,
                    capabilities = excluded.capabilities,
                    status = excluded.status
                """,
                (
                    worker_id,
                    hostname,
                    process_id,
                    _format_datetime(started),
                    _format_datetime(now),
                    json.dumps(capabilities or {}, sort_keys=True, separators=(",", ":")),
                    status,
                ),
            )
            self._insert_worker_heartbeat(worker_id, status=status, now=now, current_run_id=None, progress_summary={})
        record = self.get_worker(worker_id)
        if record is None:
            raise RuntimeError(f"failed to register worker: {worker_id}")
        return record

    def heartbeat(
        self,
        worker_id: str,
        *,
        status: WorkerStatus | str = "idle",
        current_run_id: str | None = None,
        progress_summary: dict[str, Any] | None = None,
        cpu_percent: float | None = None,
        memory_bytes: int | None = None,
    ) -> None:
        now = datetime.now(UTC)
        progress = progress_summary or {}
        with self._connection:
            existing = self.get_worker(worker_id)
            if existing is None:
                self.register_worker(worker_id, hostname="unknown", status=status)
            self._connection.execute(
                """
                UPDATE workers
                SET heartbeat_at = ?, status = ?, current_run_id = ?, progress_summary = ?,
                    cpu_percent = ?, memory_bytes = ?
                WHERE worker_id = ?
                """,
                (
                    _format_datetime(now),
                    status,
                    current_run_id,
                    json.dumps(progress, sort_keys=True, separators=(",", ":")),
                    cpu_percent,
                    memory_bytes,
                    worker_id,
                ),
            )
            self._insert_worker_heartbeat(
                worker_id,
                status=status,
                now=now,
                current_run_id=current_run_id,
                progress_summary=progress,
                cpu_percent=cpu_percent,
                memory_bytes=memory_bytes,
            )
            if current_run_id is not None:
                self._upsert_lease(run_id=current_run_id, worker_id=worker_id, now=now)

    def list_workers(self) -> list[WorkerHeartbeat]:
        return [
            WorkerHeartbeat(
                worker_id=record.worker_id,
                status=record.status,
                updated_at=record.heartbeat_at,
                current_run_id=record.current_run_id,
            )
            for record in self.list_worker_records()
        ]

    def list_worker_records(self) -> list[WorkerRecord]:
        rows = self._connection.execute("SELECT * FROM workers ORDER BY heartbeat_at DESC, worker_id ASC").fetchall()
        return [_worker_from_row(row) for row in rows]

    def get_worker(self, worker_id: str) -> WorkerRecord | None:
        row = self._connection.execute("SELECT * FROM workers WHERE worker_id = ?", (worker_id,)).fetchone()
        return _worker_from_row(row) if row is not None else None

    def drain_worker(self, worker_id: str) -> WorkerRecord | None:
        with self._connection:
            self._connection.execute("UPDATE workers SET drain_requested = 1 WHERE worker_id = ?", (worker_id,))
        return self.get_worker(worker_id)

    def shutdown_worker(self, worker_id: str) -> WorkerRecord | None:
        with self._connection:
            self._connection.execute(
                "UPDATE workers SET shutdown_requested = 1, status = 'offline' WHERE worker_id = ?", (worker_id,)
            )
        return self.get_worker(worker_id)

    def detect_stale_workers(self, *, stale_after_seconds: int | None = None) -> list[WorkerRecord]:
        timeout = stale_after_seconds or self._stale_after_seconds
        cutoff = datetime.now(UTC) - timedelta(seconds=timeout)
        with self._connection:
            self._connection.execute(
                """
                UPDATE workers
                SET status = 'stale'
                WHERE status NOT IN ('offline', 'stale') AND heartbeat_at < ?
                """,
                (_format_datetime(cutoff),),
            )
        return [worker for worker in self.list_worker_records() if worker.status == "stale"]

    def requeue_stale(self, *, stale_after_seconds: int | None = None) -> RequeueResult:
        timeout = stale_after_seconds or self._stale_after_seconds
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=timeout)
        stale_workers = self.detect_stale_workers(stale_after_seconds=timeout)
        rows = self._connection.execute(
            """
            SELECT run_id FROM run_queue
            WHERE status = 'running' AND locked_at IS NOT NULL AND locked_at < ?
            ORDER BY locked_at ASC, run_id ASC
            """,
            (_format_datetime(cutoff),),
        ).fetchall()
        requeued = [str(row["run_id"]) for row in rows]
        with self._connection:
            self._connection.execute(
                """
                UPDATE run_queue
                SET status = 'pending', available_at = ?, locked_by = NULL, locked_at = NULL,
                    last_error = 'requeued after stale worker lease expired'
                WHERE status = 'running' AND locked_at IS NOT NULL AND locked_at < ?
                """,
                (_format_datetime(now), _format_datetime(cutoff)),
            )
            for run_id in requeued:
                self._connection.execute("DELETE FROM run_leases WHERE run_id = ?", (run_id,))
            self.record_scheduler_metrics()
        return RequeueResult(stale_workers=len(stale_workers), requeued_runs=requeued)

    def list_leases(self) -> list[RunLease]:
        rows = self._connection.execute("SELECT * FROM run_leases ORDER BY expires_at ASC, run_id ASC").fetchall()
        return [_lease_from_row(row) for row in rows]

    def get_lease(self, run_id: str) -> RunLease | None:
        row = self._connection.execute("SELECT * FROM run_leases WHERE run_id = ?", (run_id,)).fetchone()
        return _lease_from_row(row) if row is not None else None

    def scheduler_status(self) -> SchedulerStatus:
        self.detect_stale_workers()
        status_counts = {row["status"]: int(row["count"]) for row in self._connection.execute(
            "SELECT status, COUNT(*) AS count FROM run_queue GROUP BY status"
        ).fetchall()}
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=self._stale_after_seconds)
        stale_job_count = int(
            self._connection.execute(
                "SELECT COUNT(*) AS count FROM run_queue WHERE status = 'running' AND locked_at IS NOT NULL AND locked_at < ?",
                (_format_datetime(stale_before),),
            ).fetchone()["count"]
        )
        workers = self.list_worker_records()
        active_workers = [worker for worker in workers if worker.status in {"idle", "busy", "running"}]
        busy_workers = [worker for worker in active_workers if worker.status in {"busy", "running"} or worker.current_run_id]
        utilization = (len(busy_workers) / len(active_workers)) if active_workers else 0.0
        average_wait, average_run = self._duration_averages(now)
        throughput = self._throughput_per_minute(now)
        return SchedulerStatus(
            pending_count=status_counts.get("pending", 0),
            running_count=status_counts.get("running", 0),
            completed_count=status_counts.get("completed", 0),
            failed_count=status_counts.get("failed", 0),
            stale_worker_count=sum(1 for worker in workers if worker.status == "stale"),
            stale_job_count=stale_job_count,
            queue_depth=status_counts.get("pending", 0) + status_counts.get("running", 0),
            average_wait_seconds=average_wait,
            average_run_seconds=average_run,
            worker_utilization=utilization,
            throughput_per_minute=throughput,
        )

    def record_scheduler_metrics(self) -> SchedulerStatus:
        status = self.scheduler_status()
        now = datetime.now(UTC)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO scheduler_metrics (
                    captured_at, queue_depth, average_wait_seconds, average_run_seconds,
                    worker_utilization, stale_job_count, failed_job_count, throughput_per_minute
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _format_datetime(now),
                    status.queue_depth,
                    status.average_wait_seconds,
                    status.average_run_seconds,
                    status.worker_utilization,
                    status.stale_job_count,
                    status.failed_count,
                    status.throughput_per_minute,
                ),
            )
        return status

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
            self._connection.execute("DELETE FROM run_leases WHERE run_id = ?", (run_id,))
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

            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                process_id INTEGER,
                started_at TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL,
                capabilities TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL,
                current_run_id TEXT,
                progress_summary TEXT NOT NULL DEFAULT '{}',
                cpu_percent REAL,
                memory_bytes INTEGER,
                drain_requested INTEGER NOT NULL DEFAULT 0,
                shutdown_requested INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS worker_heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id TEXT NOT NULL,
                status TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL,
                current_run_id TEXT,
                progress_summary TEXT NOT NULL DEFAULT '{}',
                cpu_percent REAL,
                memory_bytes INTEGER
            );

            CREATE TABLE IF NOT EXISTS run_leases (
                run_id TEXT PRIMARY KEY,
                worker_id TEXT NOT NULL,
                acquired_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scheduler_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at TEXT NOT NULL,
                queue_depth INTEGER NOT NULL,
                average_wait_seconds REAL NOT NULL,
                average_run_seconds REAL NOT NULL,
                worker_utilization REAL NOT NULL,
                stale_job_count INTEGER NOT NULL,
                failed_job_count INTEGER NOT NULL,
                throughput_per_minute REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_run_queue_claim
                ON run_queue(status, available_at, priority, created_at);
            CREATE INDEX IF NOT EXISTS idx_run_queue_locked_at ON run_queue(status, locked_at);
            CREATE INDEX IF NOT EXISTS idx_workers_status_heartbeat ON workers(status, heartbeat_at);
            CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_worker_time ON worker_heartbeats(worker_id, heartbeat_at);
            CREATE INDEX IF NOT EXISTS idx_run_leases_expires ON run_leases(expires_at);
            """
        )
        self._migrate_legacy_worker_heartbeats()
        self._connection.commit()

    def _migrate_legacy_worker_heartbeats(self) -> None:
        columns = {row["name"] for row in self._connection.execute("PRAGMA table_info(worker_heartbeats)").fetchall()}
        if "updated_at" not in columns:
            return
        rows = self._connection.execute(
            "SELECT worker_id, status, updated_at, current_run_id FROM worker_heartbeats"
        ).fetchall()
        self._connection.executescript(
            """
            ALTER TABLE worker_heartbeats RENAME TO worker_heartbeats_legacy;
            CREATE TABLE worker_heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id TEXT NOT NULL,
                status TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL,
                current_run_id TEXT,
                progress_summary TEXT NOT NULL DEFAULT '{}',
                cpu_percent REAL,
                memory_bytes INTEGER
            );
            """
        )
        for row in rows:
            self._connection.execute(
                """
                INSERT INTO workers (
                    worker_id, hostname, process_id, started_at, heartbeat_at, capabilities, status,
                    current_run_id, progress_summary, cpu_percent, memory_bytes, drain_requested, shutdown_requested
                ) VALUES (?, 'unknown', NULL, ?, ?, '{}', ?, ?, '{}', NULL, NULL, 0, 0)
                ON CONFLICT(worker_id) DO NOTHING
                """,
                (row["worker_id"], row["updated_at"], row["updated_at"], row["status"], row["current_run_id"]),
            )
            self._connection.execute(
                """
                INSERT INTO worker_heartbeats (worker_id, status, heartbeat_at, current_run_id)
                VALUES (?, ?, ?, ?)
                """,
                (row["worker_id"], row["status"], row["updated_at"], row["current_run_id"]),
            )
        self._connection.execute("DROP TABLE worker_heartbeats_legacy")

    def _insert_worker_heartbeat(
        self,
        worker_id: str,
        *,
        status: WorkerStatus | str,
        now: datetime,
        current_run_id: str | None,
        progress_summary: dict[str, Any],
        cpu_percent: float | None = None,
        memory_bytes: int | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO worker_heartbeats (
                worker_id, status, heartbeat_at, current_run_id, progress_summary, cpu_percent, memory_bytes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                worker_id,
                status,
                _format_datetime(now),
                current_run_id,
                json.dumps(progress_summary, sort_keys=True, separators=(",", ":")),
                cpu_percent,
                memory_bytes,
            ),
        )

    def _upsert_lease(self, *, run_id: str, worker_id: str, now: datetime) -> None:
        expires = now + timedelta(seconds=self._stale_after_seconds)
        self._connection.execute(
            """
            INSERT INTO run_leases (run_id, worker_id, acquired_at, expires_at, heartbeat_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                worker_id = excluded.worker_id,
                expires_at = excluded.expires_at,
                heartbeat_at = excluded.heartbeat_at
            """,
            (run_id, worker_id, _format_datetime(now), _format_datetime(expires), _format_datetime(now)),
        )
        self._connection.execute(
            "UPDATE run_queue SET locked_at = ?, locked_by = ? WHERE run_id = ? AND status = 'running'",
            (_format_datetime(now), worker_id, run_id),
        )

    def _duration_averages(self, now: datetime) -> tuple[float, float]:
        rows = self._connection.execute(
            "SELECT created_at, started_at, completed_at FROM run_queue WHERE started_at IS NOT NULL"
        ).fetchall()
        waits: list[float] = []
        durations: list[float] = []
        for row in rows:
            created = _parse_datetime(row["created_at"])
            started = _parse_datetime(row["started_at"])
            completed = _parse_optional_datetime(row["completed_at"]) or now
            waits.append(max((started - created).total_seconds(), 0.0))
            durations.append(max((completed - started).total_seconds(), 0.0))
        average_wait = sum(waits) / len(waits) if waits else 0.0
        average_run = sum(durations) / len(durations) if durations else 0.0
        return average_wait, average_run

    def _throughput_per_minute(self, now: datetime) -> float:
        since = now - timedelta(minutes=1)
        row = self._connection.execute(
            """
            SELECT COUNT(*) AS count FROM run_queue
            WHERE completed_at IS NOT NULL AND completed_at >= ? AND status IN ('completed', 'failed')
            """,
            (_format_datetime(since),),
        ).fetchone()
        return float(row["count"])


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


def _worker_from_row(row: sqlite3.Row) -> WorkerRecord:
    return WorkerRecord(
        worker_id=row["worker_id"],
        hostname=row["hostname"],
        process_id=row["process_id"],
        started_at=_parse_datetime(row["started_at"]),
        heartbeat_at=_parse_datetime(row["heartbeat_at"]),
        capabilities=_parse_json_object(row["capabilities"]),
        status=row["status"],
        current_run_id=row["current_run_id"],
        progress_summary=_parse_json_object(row["progress_summary"]),
        cpu_percent=row["cpu_percent"],
        memory_bytes=row["memory_bytes"],
        drain_requested=bool(row["drain_requested"]),
        shutdown_requested=bool(row["shutdown_requested"]),
    )


def _lease_from_row(row: sqlite3.Row) -> RunLease:
    return RunLease(
        run_id=row["run_id"],
        worker_id=row["worker_id"],
        acquired_at=_parse_datetime(row["acquired_at"]),
        expires_at=_parse_datetime(row["expires_at"]),
        heartbeat_at=_parse_datetime(row["heartbeat_at"]),
    )


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def _parse_optional_datetime(value: str | None) -> datetime | None:
    return _parse_datetime(value) if value is not None else None


def _parse_json_object(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    return parsed if isinstance(parsed, dict) else {}
