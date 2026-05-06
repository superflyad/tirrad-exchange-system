"""In-memory run storage for the TES API service."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from uuid import uuid4

from sim.api.models import RunStatus, RunType


@dataclass
class RunRecord:
    run_id: str
    run_type: RunType
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    config: dict[str, Any] = field(default_factory=dict)
    report: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[dict[str, Any]] = field(default_factory=list)
    accounts: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class InMemoryRunStore:
    """Thread-safe process-local storage for API runs.

    The interface is intentionally small so a persistent SQLite/Postgres
    implementation can replace it without changing route code.
    """

    def __init__(self) -> None:
        self._records: dict[str, RunRecord] = {}
        self._lock = RLock()

    def create_run(self, *, run_type: RunType, config: dict[str, Any]) -> RunRecord:
        now = datetime.now(UTC)
        record = RunRecord(
            run_id=uuid4().hex,
            run_type=run_type,
            status="pending",
            created_at=now,
            config=deepcopy(config),
        )
        with self._lock:
            self._records[record.run_id] = record
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
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return None
            if status is not None:
                record.status = status
            if started_at is not None:
                record.started_at = started_at
            if completed_at is not None:
                record.completed_at = completed_at
            if error is not None:
                record.error = error
            return deepcopy(record)

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            record = self._records.get(run_id)
            return deepcopy(record) if record is not None else None

    def list_runs(self) -> list[RunRecord]:
        with self._lock:
            records = sorted(self._records.values(), key=lambda item: item.created_at)
            return deepcopy(records)

    def delete_run(self, run_id: str) -> bool:
        with self._lock:
            return self._records.pop(run_id, None) is not None

    def store_result(
        self,
        run_id: str,
        *,
        report: dict[str, Any],
        events: list[dict[str, Any]],
        snapshots: list[dict[str, Any]],
        accounts: list[dict[str, Any]],
    ) -> RunRecord | None:
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return None
            record.report = deepcopy(report)
            record.events = deepcopy(events)
            record.snapshots = deepcopy(snapshots)
            record.accounts = deepcopy(accounts)
            return deepcopy(record)
