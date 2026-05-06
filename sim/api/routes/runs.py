"""Run lifecycle routes for the TES API service."""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from sim.api.models import (
    BacktestRunRequest,
    RunAccountsResponse,
    RunDetail,
    RunEventsResponse,
    RunInspectionSummary,
    RunLogsResponse,
    RunReplayResponse,
    RunReportResponse,
    RunSnapshotsResponse,
    RunSummary,
    RunTimelineResponse,
    SessionRunRequest,
    WorkerSummary,
)
from sim.api.services.replay_service import ReplayService
from sim.api.services.run_service import RunService
from sim.api.services.stream_service import StreamService

router = APIRouter(tags=["runs"])


def _service(request: Request) -> RunService:
    return request.app.state.run_service


def _replay_service(request: Request) -> ReplayService:
    return request.app.state.replay_service


def _stream_service(request: Request) -> StreamService:
    return request.app.state.stream_service


def _queue(request: Request):
    return getattr(request.app.state, "run_queue", None)


def _use_queue(payload_mode: str | None, request: Request) -> bool:
    if payload_mode == "sync":
        return False
    if payload_mode == "queued":
        return True
    return bool(getattr(request.app.state, "queue_enabled", False))


def _queued_detail(detail: RunDetail) -> RunDetail:
    return detail.model_copy(
        update={
            "polling_url": f"/runs/{detail.run_id}",
            "stream_url": f"/runs/{detail.run_id}/stream",
        }
    )


@router.post("/sessions/run", response_model=RunDetail)
def run_session(payload: SessionRunRequest, request: Request) -> RunDetail:
    if _use_queue(payload.mode, request):
        queue = _queue(request)
        if queue is None:
            return _service(request).run_session(payload)
        detail = _service(request).queue_session(payload)
        queue.enqueue(detail.run_id)
        return _queued_detail(detail)
    return _service(request).run_session(payload)


@router.post("/backtests/run", response_model=RunDetail)
def run_backtest(payload: BacktestRunRequest, request: Request) -> RunDetail:
    if _use_queue(payload.mode, request):
        queue = _queue(request)
        if queue is None:
            return _service(request).run_backtest(payload)
        detail = _service(request).queue_backtest(payload)
        queue.enqueue(detail.run_id)
        return _queued_detail(detail)
    return _service(request).run_backtest(payload)


@router.get("/runs", response_model=list[RunSummary])
def list_runs(request: Request) -> list[RunSummary]:
    return _service(request).list_runs()


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str, request: Request) -> RunDetail:
    return _service(request).get_run(run_id)


@router.get("/runs/{run_id}/stream")
def stream_run(
    run_id: str,
    request: Request,
    replay_limit: int = Query(default=100, ge=0),
) -> StreamingResponse:
    record = _service(request).get_run(run_id)
    stream_service = _stream_service(request)

    def events() -> Iterator[str]:
        for message in stream_service.replay_recent(run_id, replay_limit):
            yield _sse_message(message.model_dump(mode="json"))
        if record.status in {"completed", "failed", "canceled"} or stream_service.is_closed(run_id):
            return
        for message in stream_service.subscribe(run_id):
            yield _sse_message(message.model_dump(mode="json"))

    return StreamingResponse(events(), media_type="text/event-stream")


def _sse_message(payload: dict[str, object]) -> str:
    event_type = str(payload.get("category") or "message")
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"event: {event_type}\ndata: {data}\n\n"


@router.get("/runs/{run_id}/report", response_model=RunReportResponse)
def get_report(run_id: str, request: Request) -> RunReportResponse:
    return RunReportResponse(run_id=run_id, report=_service(request).get_report(run_id))


@router.get("/runs/{run_id}/events", response_model=RunEventsResponse)
def get_events(
    run_id: str,
    request: Request,
    symbol: str | None = None,
    event_type: str | None = None,
    limit: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0),
) -> RunEventsResponse:
    return RunEventsResponse(
        run_id=run_id,
        events=_service(request).get_events(
            run_id, symbol=symbol, event_type=event_type, limit=limit, offset=offset
        ),
    )


@router.get("/runs/{run_id}/snapshots", response_model=RunSnapshotsResponse)
def get_snapshots(
    run_id: str,
    request: Request,
    symbol: str | None = None,
    limit: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0),
) -> RunSnapshotsResponse:
    return RunSnapshotsResponse(
        run_id=run_id,
        snapshots=_service(request).get_snapshots(run_id, symbol=symbol, limit=limit, offset=offset),
    )


@router.get("/runs/{run_id}/accounts", response_model=RunAccountsResponse)
def get_accounts(
    run_id: str,
    request: Request,
    account_id: str | None = None,
    symbol: str | None = None,
) -> RunAccountsResponse:
    return RunAccountsResponse(
        run_id=run_id,
        accounts=_service(request).get_accounts(run_id, account_id=account_id, symbol=symbol),
    )


@router.get("/runs/{run_id}/logs", response_model=RunLogsResponse)
def get_logs(
    run_id: str,
    request: Request,
    limit: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0),
) -> RunLogsResponse:
    return RunLogsResponse(run_id=run_id, logs=_service(request).get_logs(run_id, limit=limit, offset=offset))


@router.get("/runs/{run_id}/timeline", response_model=RunTimelineResponse)
def get_timeline(
    run_id: str,
    request: Request,
    symbol: str | None = None,
    category: str | None = None,
    type: str | None = None,
    limit: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0),
) -> RunTimelineResponse:
    return RunTimelineResponse(
        run_id=run_id,
        timeline=_replay_service(request).get_timeline(
            run_id, symbol=symbol, category=category, entry_type=type, limit=limit, offset=offset
        ),
    )


@router.get("/runs/{run_id}/orders/{order_id}/timeline", response_model=RunTimelineResponse)
def get_order_timeline(
    run_id: str,
    order_id: str,
    request: Request,
    symbol: str | None = None,
    category: str | None = None,
    type: str | None = None,
    limit: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0),
) -> RunTimelineResponse:
    return RunTimelineResponse(
        run_id=run_id,
        timeline=_replay_service(request).get_order_timeline(
            run_id,
            order_id,
            symbol=symbol,
            category=category,
            entry_type=type,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/runs/{run_id}/accounts/{account_id}/timeline", response_model=RunTimelineResponse)
def get_account_timeline(
    run_id: str,
    account_id: str,
    request: Request,
    symbol: str | None = None,
    category: str | None = None,
    type: str | None = None,
    limit: int | None = Query(default=None, ge=0),
    offset: int = Query(default=0, ge=0),
) -> RunTimelineResponse:
    return RunTimelineResponse(
        run_id=run_id,
        timeline=_replay_service(request).get_account_timeline(
            run_id,
            account_id,
            symbol=symbol,
            category=category,
            entry_type=type,
            limit=limit,
            offset=offset,
        ),
    )


@router.post("/runs/{run_id}/replay", response_model=RunReplayResponse)
def replay_run(run_id: str, request: Request) -> RunReplayResponse:
    return _replay_service(request).replay_run(run_id)


@router.get("/runs/{run_id}/summary", response_model=RunInspectionSummary)
def summarize_run(run_id: str, request: Request) -> RunInspectionSummary:
    return _replay_service(request).summarize_run(run_id)


@router.post("/runs/{run_id}/cancel", response_model=RunDetail)
def cancel_run(run_id: str, request: Request) -> RunDetail:
    queue = _queue(request)
    if queue is not None:
        queue.cancel_pending(run_id)
    return _service(request).cancel_run(run_id)


@router.get("/workers", response_model=list[WorkerSummary])
def list_workers(request: Request) -> list[WorkerSummary]:
    queue = _queue(request)
    if queue is None:
        return []
    return [WorkerSummary(**worker.__dict__) for worker in queue.list_workers()]


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, request: Request) -> Response:
    _service(request).delete_run(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
