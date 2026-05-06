"""SQLite-backed durable run storage for the TES API service."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Iterable
from uuid import uuid4

from sim.api.models import RunStatus, RunType
from sim.api.storage.base import RunRecord

_SCHEMA_VERSION = 1
_DEFAULT_TIMEOUT_SECONDS = 5.0


class SQLiteRunStore:
    """Durable SQLite storage for local API run metadata and artifacts."""

    def __init__(self, path: str | Path, *, timeout: float = _DEFAULT_TIMEOUT_SECONDS) -> None:
        self.path = Path(path)
        if self.path == Path(":memory:"):
            database = ":memory:"
        else:
            parent = self.path.expanduser().resolve().parent
            parent.mkdir(parents=True, exist_ok=True)
            database = str(self.path)
        self._connection = sqlite3.connect(database, timeout=timeout, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._lock:
            self._configure_connection()
            self._initialize_schema()

    def create_run(self, *, run_type: RunType, config: dict[str, Any]) -> RunRecord:
        record = RunRecord(
            run_id=uuid4().hex,
            run_type=run_type,
            status="pending",
            created_at=datetime.now(UTC),
            config=deepcopy(config),
        )
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO runs (
                    run_id, run_type, status, created_at, started_at, completed_at,
                    config_json, report_json, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_id,
                    record.run_type,
                    record.status,
                    _format_datetime(record.created_at),
                    None,
                    None,
                    _encode_json(record.config),
                    None,
                    None,
                ),
            )
        return deepcopy(record)

    def update_run(
        self,
        run_id: str,
        *,
        status: RunStatus | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error: str | None = None,
    ) -> RunRecord | None:
        assignments: list[str] = []
        values: list[Any] = []
        if status is not None:
            assignments.append("status = ?")
            values.append(status)
        if started_at is not None:
            assignments.append("started_at = ?")
            values.append(_format_datetime(started_at))
        if completed_at is not None:
            assignments.append("completed_at = ?")
            values.append(_format_datetime(completed_at))
        if error is not None:
            assignments.append("error = ?")
            values.append(error)
        if assignments:
            values.append(run_id)
            with self._lock, self._connection:
                self._connection.execute(
                    f"UPDATE runs SET {', '.join(assignments)} WHERE run_id = ?",
                    tuple(values),
                )
        return self.get_run(run_id)

    def update_run_status(
        self,
        run_id: str,
        *,
        status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error: str | None = None,
    ) -> RunRecord | None:
        return self.update_run(
            run_id,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            error=error,
        )

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            row = self._connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            return self._record_from_row(row)

    def list_runs(self) -> list[RunRecord]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM runs ORDER BY created_at ASC, run_id ASC"
            ).fetchall()
            return [self._record_from_row(row) for row in rows]

    def delete_run(self, run_id: str) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
            return cursor.rowcount > 0

    def store_result(
        self,
        run_id: str,
        *,
        report: dict[str, Any],
        events: list[dict[str, Any]],
        snapshots: list[dict[str, Any]],
        accounts: list[dict[str, Any]],
        logs: list[dict[str, Any]] | None = None,
    ) -> RunRecord | None:
        if self.get_run(run_id) is None:
            return None
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO run_reports (run_id, report_json)
                VALUES (?, ?)
                ON CONFLICT(run_id) DO UPDATE SET report_json = excluded.report_json
                """,
                (run_id, _encode_json(report)),
            )
            self._connection.execute(
                "UPDATE runs SET report_json = ? WHERE run_id = ?",
                (_encode_json(report), run_id),
            )
            self._replace_payload_rows("run_events", run_id, _event_rows(run_id, events))
            self._replace_payload_rows("run_snapshots", run_id, _snapshot_rows(run_id, snapshots))
            self._replace_payload_rows("run_accounts", run_id, _account_rows(run_id, accounts))
            self._replace_payload_rows("run_logs", run_id, _log_rows(run_id, logs or []))
        return self.get_run(run_id)

    def get_report(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            if not self._run_exists(run_id):
                return None
            row = self._connection.execute(
                "SELECT report_json FROM run_reports WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                row = self._connection.execute(
                    "SELECT report_json FROM runs WHERE run_id = ?", (run_id,)
                ).fetchone()
            return _decode_json(row["report_json"] if row else None, {})

    def get_events(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        if not self._run_exists(run_id):
            return None
        clauses = ["run_id = ?"]
        values: list[Any] = [run_id]
        if symbol is not None:
            clauses.append("symbol = ?")
            values.append(symbol)
        if event_type is not None:
            clauses.append("event_type = ?")
            values.append(event_type)
        return self._fetch_payloads(
            "run_events",
            clauses,
            values,
            order_by="sequence ASC",
            limit=limit,
            offset=offset,
        )

    def get_snapshots(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        if not self._run_exists(run_id):
            return None
        clauses = ["run_id = ?"]
        values: list[Any] = [run_id]
        if symbol is not None:
            clauses.append("symbol = ?")
            values.append(symbol)
        return self._fetch_payloads(
            "run_snapshots",
            clauses,
            values,
            order_by="step ASC, sequence ASC",
            limit=limit,
            offset=offset,
        )

    def get_accounts(
        self,
        run_id: str,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]] | None:
        if not self._run_exists(run_id):
            return None
        clauses = ["run_id = ?"]
        values: list[Any] = [run_id]
        if account_id is not None:
            clauses.append("account_id = ?")
            values.append(account_id)
        if symbol is not None:
            clauses.append("symbol = ?")
            values.append(symbol)
        return self._fetch_payloads(
            "run_accounts", clauses, values, order_by="sequence ASC", limit=None, offset=0
        )

    def get_logs(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        if not self._run_exists(run_id):
            return None
        return self._fetch_payloads(
            "run_logs",
            ["run_id = ?"],
            [run_id],
            order_by="sequence ASC",
            limit=limit,
            offset=offset,
        )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _configure_connection(self) -> None:
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        if self.path != Path(":memory:"):
            self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = NORMAL")

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT OR IGNORE INTO schema_metadata (key, value) VALUES ('schema_version', '1');

            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                run_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                config_json TEXT NOT NULL,
                report_json TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS run_reports (
                run_id TEXT PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
                report_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS run_events (
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                sequence INTEGER NOT NULL,
                event_type TEXT,
                symbol TEXT,
                step INTEGER,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (run_id, sequence)
            );

            CREATE TABLE IF NOT EXISTS run_snapshots (
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                sequence INTEGER NOT NULL,
                step INTEGER,
                symbol TEXT,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (run_id, sequence)
            );

            CREATE TABLE IF NOT EXISTS run_accounts (
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                sequence INTEGER NOT NULL,
                account_id TEXT,
                symbol TEXT,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (run_id, sequence)
            );

            CREATE TABLE IF NOT EXISTS run_logs (
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                sequence INTEGER NOT NULL,
                level TEXT,
                message TEXT,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (run_id, sequence)
            );

            CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id);
            CREATE INDEX IF NOT EXISTS idx_runs_run_type ON runs(run_type);
            CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
            CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);
            CREATE INDEX IF NOT EXISTS idx_run_events_lookup ON run_events(run_id, sequence);
            CREATE INDEX IF NOT EXISTS idx_run_events_symbol ON run_events(run_id, symbol, sequence);
            CREATE INDEX IF NOT EXISTS idx_run_events_type ON run_events(run_id, event_type, sequence);
            CREATE INDEX IF NOT EXISTS idx_run_snapshots_lookup ON run_snapshots(run_id, step, sequence);
            CREATE INDEX IF NOT EXISTS idx_run_snapshots_symbol ON run_snapshots(run_id, symbol, step, sequence);
            CREATE INDEX IF NOT EXISTS idx_run_accounts_lookup ON run_accounts(run_id, account_id, symbol);
            CREATE INDEX IF NOT EXISTS idx_run_logs_lookup ON run_logs(run_id, sequence);
            """
        )
        self._connection.commit()

    def _record_from_row(self, row: sqlite3.Row) -> RunRecord:
        run_id = row["run_id"]
        return RunRecord(
            run_id=run_id,
            run_type=row["run_type"],
            status=row["status"],
            created_at=_parse_datetime(row["created_at"]),
            started_at=_parse_datetime(row["started_at"]),
            completed_at=_parse_datetime(row["completed_at"]),
            config=_decode_json(row["config_json"], {}),
            report=self.get_report(run_id) or {},
            events=self.get_events(run_id) or [],
            snapshots=self.get_snapshots(run_id) or [],
            accounts=self.get_accounts(run_id) or [],
            error=row["error"],
        )

    def _replace_payload_rows(self, table: str, run_id: str, rows: Iterable[tuple[Any, ...]]) -> None:
        self._connection.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
        columns = _TABLE_COLUMNS[table]
        placeholders = ", ".join("?" for _ in columns)
        self._connection.executemany(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
            list(rows),
        )

    def _run_exists(self, run_id: str) -> bool:
        with self._lock:
            row = self._connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            return row is not None

    def _fetch_payloads(
        self,
        table: str,
        clauses: list[str],
        values: list[Any],
        *,
        order_by: str,
        limit: int | None,
        offset: int,
    ) -> list[dict[str, Any]]:
        sql = f"SELECT payload_json FROM {table} WHERE {' AND '.join(clauses)} ORDER BY {order_by}"
        params = list(values)
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([max(0, limit), max(0, offset)])
        elif offset > 0:
            sql += " LIMIT -1 OFFSET ?"
            params.append(offset)
        with self._lock:
            rows = self._connection.execute(sql, tuple(params)).fetchall()
        return [_decode_json(row["payload_json"], {}) for row in rows]


_TABLE_COLUMNS = {
    "run_events": ("run_id", "sequence", "event_type", "symbol", "step", "payload_json"),
    "run_snapshots": ("run_id", "sequence", "step", "symbol", "payload_json"),
    "run_accounts": ("run_id", "sequence", "account_id", "symbol", "payload_json"),
    "run_logs": ("run_id", "sequence", "level", "message", "payload_json"),
}


def _encode_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _decode_json(value: str | None, fallback: Any) -> Any:
    if value is None:
        return deepcopy(fallback)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return deepcopy(fallback)


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _event_rows(run_id: str, events: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [
        (
            run_id,
            index,
            _string_or_none(event.get("type")),
            _event_symbol(event),
            _int_or_none(event.get("step") or _dict_value(event.get("data"), "step")),
            _encode_json(event),
        )
        for index, event in enumerate(events)
    ]


def _snapshot_rows(run_id: str, snapshots: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for index, snapshot in enumerate(snapshots):
        symbols = snapshot.get("symbols")
        if isinstance(symbols, dict) and len(symbols) == 1:
            symbol = next(iter(symbols))
        else:
            symbol = _string_or_none(snapshot.get("symbol"))
        rows.append((run_id, index, _int_or_none(snapshot.get("step")), symbol, _encode_json(snapshot)))
    return rows


def _account_rows(run_id: str, accounts: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for index, account in enumerate(accounts):
        rows.append(
            (
                run_id,
                index,
                _string_or_none(account.get("account_id")),
                _account_symbol(account),
                _encode_json(account),
            )
        )
    return rows


def _log_rows(run_id: str, logs: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [
        (
            run_id,
            index,
            _string_or_none(log.get("level")),
            _string_or_none(log.get("message")),
            _encode_json(log),
        )
        for index, log in enumerate(logs)
    ]


def _event_symbol(event: dict[str, Any]) -> str | None:
    direct = _string_or_none(event.get("symbol"))
    if direct is not None:
        return direct
    return _string_or_none(_dict_value(event.get("data"), "symbol"))


def _account_symbol(account: dict[str, Any]) -> str | None:
    direct = _string_or_none(account.get("symbol"))
    if direct is not None:
        return direct
    positions = account.get("positions")
    if isinstance(positions, dict) and len(positions) == 1:
        return next(iter(positions))
    mtm = account.get("mark_to_market")
    if isinstance(mtm, dict) and len(mtm) == 1:
        return next(iter(mtm))
    return None


def _dict_value(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, dict) else None


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
