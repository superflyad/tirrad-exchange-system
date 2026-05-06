"""Run lifecycle orchestration for TES API simulations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sim.api.errors import InvalidRequestError, RunExecutionError, RunNotFoundError
from sim.api.models import BacktestRunRequest, RunDetail, RunSummary, SessionRunRequest
from sim.api.services.backtest_service import run_backtest
from sim.api.services.session_service import run_session
from sim.api.services.stream_service import StreamService
from sim.api.storage import RunRecord, RunStore


class RunService:
    """Coordinates run creation, synchronous execution, and result storage."""

    def __init__(self, store: RunStore, stream_service: StreamService | None = None) -> None:
        self._store = store
        self._stream_service = stream_service

    def queue_session(self, request: SessionRunRequest) -> RunDetail:
        record = self._store.create_run(run_type="session", config=request.model_dump(exclude={"mode"}))
        self._publish(record.run_id, "status", "run_queued", {"run_type": "session", "config": record.config})
        return self._to_detail(record)

    def queue_backtest(self, request: BacktestRunRequest) -> RunDetail:
        record = self._store.create_run(run_type="backtest", config=request.model_dump(exclude={"mode"}))
        self._publish(record.run_id, "status", "run_queued", {"run_type": "backtest", "config": record.config})
        return self._to_detail(record)

    def execute_pending_run(self, run_id: str) -> RunDetail:
        record = self._require_run(run_id)
        if record.status == "completed":
            raise InvalidRequestError(f"run is already completed: {run_id}")
        if record.status == "canceled":
            raise InvalidRequestError(f"run is canceled: {run_id}")
        if record.run_type == "session":
            request = SessionRunRequest(**record.config)
            return self._execute_existing(
                record,
                lambda claimed_run_id: run_session(
                    request, run_id=claimed_run_id, progress_callback=self._progress_publisher(claimed_run_id)
                ),
            )
        if record.run_type == "backtest":
            request = BacktestRunRequest(**record.config)
            return self._execute_existing(
                record,
                lambda claimed_run_id: run_backtest(
                    request, run_id=claimed_run_id, progress_callback=self._progress_publisher(claimed_run_id)
                ),
            )
        raise InvalidRequestError(f"unsupported run type: {record.run_type}")

    def cancel_run(self, run_id: str) -> RunDetail:
        record = self._require_run(run_id)
        if record.status == "completed":
            raise InvalidRequestError(f"completed run cannot be canceled: {run_id}")
        if record.status == "canceled":
            return self._to_detail(record)
        now = datetime.now(UTC)
        updated = self._store.update_run(
            run_id,
            status="canceled",
            completed_at=now if record.status == "pending" else None,
            error="canceled",
        )
        if updated is None:
            raise RunNotFoundError(run_id)
        self._store.append_log(
            run_id,
            {
                "level": "warning",
                "message": "run cancellation requested",
                "status": record.status,
                "timestamp": now.isoformat(),
            },
        )
        self._publish(run_id, "status", "run_canceled", {"previous_status": record.status})
        if record.status == "pending":
            self._close_stream(run_id)
        return self._to_detail(updated)

    def run_session(self, request: SessionRunRequest) -> RunDetail:
        return self._execute(
            "session",
            request.model_dump(exclude={"mode"}),
            lambda run_id: run_session(
                request, run_id=run_id, progress_callback=self._progress_publisher(run_id)
            ),
        )

    def run_backtest(self, request: BacktestRunRequest) -> RunDetail:
        return self._execute(
            "backtest",
            request.model_dump(exclude={"mode"}),
            lambda run_id: run_backtest(
                request, run_id=run_id, progress_callback=self._progress_publisher(run_id)
            ),
        )

    def list_runs(self) -> list[RunSummary]:
        return [self._to_summary(record) for record in self._store.list_runs()]

    def get_run(self, run_id: str) -> RunDetail:
        return self._to_detail(self._require_run(run_id))

    def get_report(self, run_id: str) -> dict[str, Any]:
        report = self._store.get_report(run_id)
        if report is None:
            raise RunNotFoundError(run_id)
        return report

    def get_events(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        events = self._store.get_events(
            run_id, symbol=symbol, event_type=event_type, limit=limit, offset=offset
        )
        if events is None:
            raise RunNotFoundError(run_id)
        return events

    def get_snapshots(
        self,
        run_id: str,
        *,
        symbol: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        snapshots = self._store.get_snapshots(run_id, symbol=symbol, limit=limit, offset=offset)
        if snapshots is None:
            raise RunNotFoundError(run_id)
        return snapshots

    def get_accounts(
        self,
        run_id: str,
        *,
        account_id: str | None = None,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        accounts = self._store.get_accounts(run_id, account_id=account_id, symbol=symbol)
        if accounts is None:
            raise RunNotFoundError(run_id)
        return accounts

    def get_logs(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        logs = self._store.get_logs(run_id, limit=limit, offset=offset)
        if logs is None:
            raise RunNotFoundError(run_id)
        return logs

    def delete_run(self, run_id: str) -> None:
        if not self._store.delete_run(run_id):
            raise RunNotFoundError(run_id)
        if self._stream_service is not None:
            self._stream_service.close(run_id)

    def _execute_existing(
        self, record: RunRecord, executor: Callable[[str], dict[str, Any]]
    ) -> RunDetail:
        return self._execute_record(record, record.run_type, record.config, executor)

    def _execute(
        self, run_type: str, config: dict[str, Any], executor: Callable[[str], dict[str, Any]]
    ) -> RunDetail:
        record = self._store.create_run(run_type=run_type, config=config)
        return self._execute_record(record, run_type, config, executor)

    def _execute_record(
        self,
        record: RunRecord,
        run_type: str,
        config: dict[str, Any],
        executor: Callable[[str], dict[str, Any]],
    ) -> RunDetail:
        now = datetime.now(UTC)
        self._store.update_run(record.run_id, status="running", started_at=now)
        self._publish(record.run_id, "status", "run_started", {"run_type": run_type, "config": config})
        try:
            result = executor(record.run_id)
        except InvalidRequestError as exc:
            self._store.update_run(
                record.run_id,
                status="failed",
                completed_at=datetime.now(UTC),
                error="invalid request",
            )
            self._publish(record.run_id, "error", "run_failed", {"error": str(exc) or "invalid request"})
            self._close_stream(record.run_id)
            raise
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            self._store.update_run(
                record.run_id,
                status="failed",
                completed_at=datetime.now(UTC),
                error=message,
            )
            self._publish(record.run_id, "error", "run_failed", {"error": message})
            self._close_stream(record.run_id)
            raise RunExecutionError(message) from exc

        self._publish_result_streams(record.run_id, config, result)
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
        self._publish(record.run_id, "completed", "run_completed", self._completion_payload(result))
        self._close_stream(record.run_id)
        return self._to_detail(completed)

    def _progress_publisher(self, run_id: str) -> Callable[[dict[str, Any]], None]:
        def publish_progress(payload: dict[str, Any]) -> None:
            step = payload.get("step") if isinstance(payload.get("step"), int) else None
            self._publish(run_id, "progress", "progress", payload, step=step)
        return publish_progress

    def _publish_result_streams(self, run_id: str, config: dict[str, Any], result: dict[str, Any]) -> None:
        if bool(config.get("stream_events", False)):
            for event in result.get("events", []):
                if isinstance(event, dict):
                    data = event.get("data", {}) if isinstance(event.get("data"), dict) else {}
                    step = event.get("step") or data.get("step")
                    self._publish(
                        run_id,
                        "event",
                        str(event.get("type", "event")),
                        event,
                        step=step if isinstance(step, int) else None,
                    )
        if bool(config.get("stream_snapshots", False)):
            for snapshot in result.get("snapshots", []):
                if isinstance(snapshot, dict):
                    step = snapshot.get("step") if isinstance(snapshot.get("step"), int) else None
                    self._publish(run_id, "snapshot", "snapshot", snapshot, step=step)

    def _completion_payload(self, result: dict[str, Any]) -> dict[str, Any]:
        report = result.get("report") if isinstance(result.get("report"), dict) else {}
        return {
            "report_summary": self._report_summary(report),
            "total_events": len(result.get("events", [])),
            "total_snapshots": len(result.get("snapshots", [])),
            "total_accounts": len(result.get("accounts", [])),
        }

    def _publish(
        self,
        run_id: str,
        category: str,
        message_type: str,
        payload: dict[str, Any],
        *,
        step: int | None = None,
    ) -> None:
        if self._stream_service is not None:
            self._stream_service.publish(
                run_id,
                {"category": category, "type": message_type, "payload": payload, "step": step},
            )

    def _close_stream(self, run_id: str) -> None:
        if self._stream_service is not None:
            self._stream_service.close(run_id)

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
