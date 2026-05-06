"""Distributed scheduler and worker orchestration routes."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from sim.api.errors import RunNotFoundError
from sim.api.models import RequeueStaleResponse, SchedulerStatusResponse, WorkerSummary

router = APIRouter(tags=["scheduler"])


def _scheduler(request: Request):
    return getattr(request.app.state, "scheduler_service", None)


def _require_scheduler(request: Request):
    scheduler = _scheduler(request)
    if scheduler is None:
        raise RunNotFoundError("scheduler")
    return scheduler


@router.get("/workers", response_model=list[WorkerSummary])
def list_workers(request: Request) -> list[WorkerSummary]:
    scheduler = _scheduler(request)
    if scheduler is None:
        return []
    return [WorkerSummary.from_record(worker) for worker in scheduler.registry.list_workers()]


@router.get("/workers/{worker_id}", response_model=WorkerSummary)
def get_worker(worker_id: str, request: Request) -> WorkerSummary:
    worker = _require_scheduler(request).registry.get_worker(worker_id)
    if worker is None:
        raise RunNotFoundError(worker_id)
    return WorkerSummary.from_record(worker)


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
def scheduler_status(request: Request) -> SchedulerStatusResponse:
    scheduler = _scheduler(request)
    if scheduler is None:
        return SchedulerStatusResponse(
            pending_count=0,
            running_count=0,
            completed_count=0,
            failed_count=0,
            stale_worker_count=0,
            stale_job_count=0,
            queue_depth=0,
            average_wait_seconds=0.0,
            average_run_seconds=0.0,
            worker_utilization=0.0,
            throughput_per_minute=0.0,
        )
    return SchedulerStatusResponse(**scheduler.status())


@router.post("/scheduler/requeue-stale", response_model=RequeueStaleResponse)
def requeue_stale(
    request: Request,
    stale_after_seconds: int | None = Query(default=None, gt=0),
) -> RequeueStaleResponse:
    return RequeueStaleResponse(**_require_scheduler(request).requeue_stale(stale_after_seconds=stale_after_seconds))


@router.post("/workers/{worker_id}/drain", response_model=WorkerSummary)
def drain_worker(worker_id: str, request: Request) -> WorkerSummary:
    worker = _require_scheduler(request).registry.drain(worker_id)
    if worker is None:
        raise RunNotFoundError(worker_id)
    return WorkerSummary.from_record(worker)


@router.post("/workers/{worker_id}/shutdown", response_model=WorkerSummary)
def shutdown_worker(worker_id: str, request: Request) -> WorkerSummary:
    worker = _require_scheduler(request).registry.shutdown(worker_id)
    if worker is None:
        raise RunNotFoundError(worker_id)
    return WorkerSummary.from_record(worker)
