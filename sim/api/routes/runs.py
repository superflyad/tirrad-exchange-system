"""Run lifecycle routes for the TES API service."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from sim.api.models import (
    BacktestRunRequest,
    RunAccountsResponse,
    RunDetail,
    RunEventsResponse,
    RunReportResponse,
    RunSnapshotsResponse,
    RunSummary,
    SessionRunRequest,
)
from sim.api.services.run_service import RunService

router = APIRouter(tags=["runs"])


def _service(request: Request) -> RunService:
    return request.app.state.run_service


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
def get_events(run_id: str, request: Request) -> RunEventsResponse:
    return RunEventsResponse(run_id=run_id, events=_service(request).get_events(run_id))


@router.get("/runs/{run_id}/snapshots", response_model=RunSnapshotsResponse)
def get_snapshots(run_id: str, request: Request) -> RunSnapshotsResponse:
    return RunSnapshotsResponse(run_id=run_id, snapshots=_service(request).get_snapshots(run_id))


@router.get("/runs/{run_id}/accounts", response_model=RunAccountsResponse)
def get_accounts(run_id: str, request: Request) -> RunAccountsResponse:
    return RunAccountsResponse(run_id=run_id, accounts=_service(request).get_accounts(run_id))


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, request: Request) -> Response:
    _service(request).delete_run(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
