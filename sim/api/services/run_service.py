"""Run lifecycle orchestration for TES API simulations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sim.api.errors import InvalidRequestError, RunExecutionError, RunNotFoundError
from sim.api.models import BacktestRunRequest, RunDetail, RunSummary, SessionRunRequest
from sim.api.services.backtest_service import run_backtest
from sim.api.services.session_service import run_session
from sim.api.storage.in_memory import InMemoryRunStore, RunRecord


class RunService:
    """Coordinates run creation, synchronous execution, and result storage."""

    def __init__(self, store: InMemoryRunStore) -> None:
        self._store = store

    def run_session(self, request: SessionRunRequest) -> RunDetail:
        return self._execute("session", request.model_dump(), lambda: run_session(request))

    def run_backtest(self, request: BacktestRunRequest) -> RunDetail:
        return self._execute("backtest", request.model_dump(), lambda: run_backtest(request))

    def list_runs(self) -> list[RunSummary]:
        return [self._to_summary(record) for record in self._store.list_runs()]

    def get_run(self, run_id: str) -> RunDetail:
        return self._to_detail(self._require_run(run_id))

    def get_report(self, run_id: str) -> dict[str, Any]:
        return self._require_run(run_id).report

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        return self._require_run(run_id).events

    def get_snapshots(self, run_id: str) -> list[dict[str, Any]]:
        return self._require_run(run_id).snapshots

    def get_accounts(self, run_id: str) -> list[dict[str, Any]]:
        return self._require_run(run_id).accounts

    def delete_run(self, run_id: str) -> None:
        if not self._store.delete_run(run_id):
            raise RunNotFoundError(run_id)

    def _execute(self, run_type: str, config: dict[str, Any], executor: object) -> RunDetail:
        record = self._store.create_run(run_type=run_type, config=config)
        now = datetime.now(UTC)
        self._store.update_run(record.run_id, status="running", started_at=now)
        try:
            result = executor()
        except InvalidRequestError:
            self._store.update_run(
                record.run_id,
                status="failed",
                completed_at=datetime.now(UTC),
                error="invalid request",
            )
            raise
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            self._store.update_run(
                record.run_id,
                status="failed",
                completed_at=datetime.now(UTC),
                error=message,
            )
            raise RunExecutionError(message) from exc

        self._store.store_result(
            record.run_id,
            report=result["report"],
            events=result["events"],
            snapshots=result["snapshots"],
            accounts=result["accounts"],
        )
        completed = self._store.update_run(
            record.run_id,
            status="completed",
            completed_at=datetime.now(UTC),
        )
        if completed is None:
            raise RunNotFoundError(record.run_id)
        return self._to_detail(completed)

    def _require_run(self, run_id: str) -> RunRecord:
        record = self._store.get_run(run_id)
        if record is None:
            raise RunNotFoundError(run_id)
        return record

    def _to_summary(self, record: RunRecord) -> RunSummary:
        return RunSummary(
            run_id=record.run_id,
            run_type=record.run_type,
            status=record.status,
            created_at=record.created_at,
            started_at=record.started_at,
            completed_at=record.completed_at,
            config=record.config,
            report_summary=self._report_summary(record.report),
            error=record.error,
        )

    def _to_detail(self, record: RunRecord) -> RunDetail:
        summary = self._to_summary(record)
        return RunDetail(**summary.model_dump(), report=record.report)

    def _report_summary(self, report: dict[str, Any]) -> dict[str, Any]:
        summary_keys = (
            "total_steps",
            "total_orders",
            "total_trades",
            "total_volume",
            "ending_equity",
            "final_equity",
            "rejected_orders",
        )
        return {key: report[key] for key in summary_keys if key in report}
