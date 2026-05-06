"""Tournament lifecycle orchestration for TES API batch runs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sim.api.errors import InvalidRequestError, RunNotFoundError
from sim.api.models import RunDetail, TournamentConfig, TournamentReport, TournamentRun
from sim.api.storage import RunStore, TournamentRecord
from sim.api.tournaments import build_report, expand_tournament


class TournamentService:
    """Creates tournament parents, links children, and aggregates reports."""

    def __init__(self, store: RunStore, run_service: Any, queue: Any | None = None) -> None:
        self._store = store
        self._run_service = run_service
        self._queue = queue

    def run_tournament(self, request: TournamentConfig) -> TournamentRun:
        try:
            specs = expand_tournament(request)
        except ValueError as exc:
            raise InvalidRequestError(str(exc)) from exc
        record = self._store.create_tournament(
            tournament_type=request.tournament_type,
            config=request.model_dump(exclude={"mode"}),
        )
        self._store.update_tournament(record.tournament_id, status="running", started_at=datetime.now(UTC))
        for spec in specs:
            child = self._store.create_run(run_type=spec.run_type, config=spec.config)
            self._store.link_tournament_child(
                record.tournament_id,
                child_run_id=child.run_id,
                child_key=spec.child_key,
                run_type=spec.run_type,
                dimensions=spec.dimensions,
            )
            if self._queue is not None:
                self._queue.enqueue(child.run_id)
        return self.get_tournament(record.tournament_id)

    def list_tournaments(self) -> list[TournamentRun]:
        return [self._to_run(record) for record in self._store.list_tournaments()]

    def get_tournament(self, tournament_id: str) -> TournamentRun:
        return self._to_run(self._require_tournament(tournament_id))

    def get_children(self, tournament_id: str) -> list[dict[str, Any]]:
        self._require_tournament(tournament_id)
        children = self._store.list_tournament_children(tournament_id)
        if children is None:
            raise RunNotFoundError(tournament_id)
        enriched: list[dict[str, Any]] = []
        for child in children:
            detail: RunDetail | None = None
            try:
                detail = self._run_service.get_run(str(child["child_run_id"]))
            except Exception:
                detail = None
            enriched.append(child | {"run": detail.model_dump(mode="json") if detail is not None else None})
        return enriched

    def get_report(self, tournament_id: str) -> TournamentReport:
        record = self._require_tournament(tournament_id)
        if record.report:
            return TournamentReport(**record.report)
        return TournamentReport(**self.aggregate(tournament_id))

    def aggregate(self, tournament_id: str) -> dict[str, Any]:
        record = self._require_tournament(tournament_id)
        children = self._store.list_tournament_children(tournament_id)
        if children is None:
            raise RunNotFoundError(tournament_id)
        child_records = []
        for child in children:
            run = self._store.get_run(str(child["child_run_id"]))
            if run is not None:
                child_records.append(run)
        report = build_report(tournament_id, children, child_records)
        completed_at = datetime.now(UTC) if report["status"] in {"completed", "failed", "canceled"} else None
        updated = self._store.update_tournament(
            tournament_id,
            status=report["status"],
            completed_at=completed_at,
            report=report,
        )
        if updated is None:
            raise RunNotFoundError(tournament_id)
        return report

    def aggregate_for_child(self, child_run_id: str) -> None:
        for tournament in self._store.list_tournaments():
            children = self._store.list_tournament_children(tournament.tournament_id) or []
            if any(child["child_run_id"] == child_run_id for child in children):
                self.aggregate(tournament.tournament_id)

    def cancel_tournament(self, tournament_id: str) -> TournamentRun:
        record = self._require_tournament(tournament_id)
        if record.status == "completed":
            raise InvalidRequestError(f"completed tournament cannot be canceled: {tournament_id}")
        children = self._store.list_tournament_children(tournament_id) or []
        for child in children:
            child_run_id = str(child["child_run_id"])
            if self._queue is not None:
                self._queue.cancel_pending(child_run_id)
            try:
                run = self._store.get_run(child_run_id)
                if run is not None and run.status in {"pending", "running"}:
                    self._run_service.cancel_run(child_run_id)
            except Exception:
                pass
        updated = self._store.update_tournament(
            tournament_id,
            status="canceled",
            completed_at=datetime.now(UTC),
            error="canceled",
        )
        if updated is None:
            raise RunNotFoundError(tournament_id)
        return self._to_run(updated)

    def _require_tournament(self, tournament_id: str) -> TournamentRecord:
        record = self._store.get_tournament(tournament_id)
        if record is None:
            raise RunNotFoundError(tournament_id)
        return record

    def _to_run(self, record: TournamentRecord) -> TournamentRun:
        children = self._store.list_tournament_children(record.tournament_id) or []
        child_records = [self._store.get_run(str(child["child_run_id"])) for child in children]
        completed = sum(1 for child in child_records if child is not None and child.status == "completed")
        failed = sum(1 for child in child_records if child is not None and child.status == "failed")
        return TournamentRun(
            tournament_id=record.tournament_id,
            status=record.status,
            tournament_type=record.tournament_type,
            created_at=record.created_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            config=record.config,
            child_count=len(children),
            completed_child_count=completed,
            failed_child_count=failed,
            error=record.error,
        )
