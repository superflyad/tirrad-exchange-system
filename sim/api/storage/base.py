"""Run storage contracts shared by TES API storage backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from sim.api.models import RunStatus, RunType


@dataclass
class RunRecord:
    """Strict API-facing run record used by all run storage backends."""

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
    logs: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


class RunStore(Protocol):
    """Storage interface for API run lifecycle and result artifacts."""

    def create_run(self, *, run_type: RunType, config: dict[str, Any]) -> RunRecord: ...

    def update_run(
        self,
        run_id: str,
        *,
        status: RunStatus | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error: str | None = None,
    ) -> RunRecord | None: ...

    def update_run_status(
        self,
        run_id: str,
        *,
        status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error: str | None = None,
    ) -> RunRecord | None: ...

    def get_run(self, run_id: str) -> RunRecord | None: ...

    def list_runs(self) -> list[RunRecord]: ...

    def delete_run(self, run_id: str) -> bool: ...

    def store_result(
        self,
        run_id: str,
        *,
        report: dict[str, Any],
        events: list[dict[str, Any]],
        snapshots: list[dict[str, Any]],
        accounts: list[dict[str, Any]],
        logs: list[dict[str, Any]] | None = None,
    ) -> RunRecord | None: ...

    def get_report(self, run_id: str) -> dict[str, Any] | None: ...

    def get_events(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None: ...

    def get_snapshots(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None: ...

    def get_accounts(
        self,
        run_id: str,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None: ...

    def get_logs(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]] | None: ...

    def append_log(self, run_id: str, log: dict[str, Any]) -> bool: ...
