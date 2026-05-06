"""In-memory run storage for the TES API service."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from uuid import uuid4

from sim.api.models import RunStatus, RunType
from sim.api.storage.base import RunRecord


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

    def get_report(self, run_id: str) -> dict[str, Any] | None:
        record = self.get_run(run_id)
        return record.report if record is not None else None

    def get_events(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        record = self.get_run(run_id)
        if record is None:
            return None
        events = [event for event in record.events if _matches_event(event, symbol=symbol, event_type=event_type)]
        return deepcopy(_page(events, limit=limit, offset=offset))

    def get_snapshots(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        record = self.get_run(run_id)
        if record is None:
            return None
        snapshots = [snapshot for snapshot in record.snapshots if _matches_symbol(snapshot, symbol)]
        return deepcopy(_page(snapshots, limit=limit, offset=offset))

    def get_accounts(
        self,
        run_id: str,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]] | None:
        record = self.get_run(run_id)
        if record is None:
            return None
        accounts = [
            account
            for account in record.accounts
            if _matches_account(account, account_id=account_id, symbol=symbol)
        ]
        return deepcopy(accounts)

    def get_logs(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None:
        return [] if self.get_run(run_id) is not None else None

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
        with self._lock:
            record = self._records.get(run_id)
            if record is None:
                return None
            record.report = deepcopy(report)
            record.events = deepcopy(events)
            record.snapshots = deepcopy(snapshots)
            record.accounts = deepcopy(accounts)
            return deepcopy(record)


def _page(items: list[dict[str, Any]], *, limit: int | None, offset: int) -> list[dict[str, Any]]:
    start = max(0, offset)
    if limit is None:
        return items[start:]
    return items[start : start + max(0, limit)]


def _event_symbol(event: dict[str, Any]) -> str | None:
    data = event.get("data")
    if isinstance(data, dict):
        value = data.get("symbol")
        return value if isinstance(value, str) else None
    value = event.get("symbol")
    return value if isinstance(value, str) else None


def _matches_event(event: dict[str, Any], *, symbol: str | None, event_type: str | None) -> bool:
    if event_type is not None and event.get("type") != event_type:
        return False
    return symbol is None or _event_symbol(event) == symbol


def _matches_symbol(payload: dict[str, Any], symbol: str | None) -> bool:
    if symbol is None:
        return True
    value = payload.get("symbol")
    if value == symbol:
        return True
    symbols = payload.get("symbols")
    return isinstance(symbols, dict) and symbol in symbols


def _matches_account(payload: dict[str, Any], *, account_id: str | None, symbol: str | None) -> bool:
    if account_id is not None and str(payload.get("account_id")) != account_id:
        return False
    if symbol is None:
        return True
    positions = payload.get("positions")
    mtm = payload.get("mark_to_market")
    return (isinstance(positions, dict) and symbol in positions) or (isinstance(mtm, dict) and symbol in mtm)
