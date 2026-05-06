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
    verification: dict[str, Any] = field(default_factory=dict)


@dataclass
class TournamentRecord:
    """Strict API-facing tournament metadata stored by TES backends."""

    tournament_id: str
    tournament_type: str
    status: RunStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    config: dict[str, Any] = field(default_factory=dict)
    report: dict[str, Any] = field(default_factory=dict)
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

    def store_verification(self, run_id: str, report: dict[str, Any]) -> dict[str, Any] | None: ...

    def get_verification(self, run_id: str) -> dict[str, Any] | None: ...

    def create_tournament(self, *, tournament_type: str, config: dict[str, Any]) -> TournamentRecord: ...

    def update_tournament(
        self,
        tournament_id: str,
        *,
        status: RunStatus | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        report: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> TournamentRecord | None: ...

    def get_tournament(self, tournament_id: str) -> TournamentRecord | None: ...

    def list_tournaments(self) -> list[TournamentRecord]: ...

    def link_tournament_child(
        self,
        tournament_id: str,
        *,
        child_run_id: str,
        child_key: str,
        run_type: RunType,
        dimensions: dict[str, Any],
    ) -> None: ...

    def list_tournament_children(self, tournament_id: str) -> list[dict[str, Any]] | None: ...
