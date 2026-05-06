"""Run lifecycle routes for the TES API service."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request, Response, status

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
)
from sim.api.services.replay_service import ReplayService
from sim.api.services.run_service import RunService

router = APIRouter(tags=["runs"])


def _service(request: Request) -> RunService:
    return request.app.state.run_service


def _replay_service(request: Request) -> ReplayService:
    return request.app.state.replay_service


@router.post("/sessions/run", response_model=RunDetail)
def run_session(payload: SessionRunRequest, request: Request) -> RunDetail:
    return _service(request).run_session(payload)


@router.post("/backtests/run", response_model=RunDetail)
def run_backtest(payload: BacktestRunRequest, request: Request) -> RunDetail:
    return _service(request).run_backtest(payload)


@router.get("/runs", response_model=list[RunSummary])
def list_runs(request: Request) -> list[RunSummary]:
    return _service(request).list_runs()


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str, request: Request) -> RunDetail:
    return _service(request).get_run(run_id)


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


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, request: Request) -> Response:
    _service(request).delete_run(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
