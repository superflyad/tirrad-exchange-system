"""Benchmark routes for TES API performance tracking."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from sim.api.models import (
    BenchmarkCompareRequest,
    BenchmarkComparisonModel,
    BenchmarkRunModel,
    BenchmarkRunRequest,
    RunDetail,
)
from sim.api.services.benchmark_service import BenchmarkService

router = APIRouter(tags=["benchmarks"])


def _service(request: Request) -> BenchmarkService:
    return request.app.state.benchmark_service


def _queue(request: Request):
    return getattr(request.app.state, "run_queue", None)


def _use_queue(payload_mode: str | None, request: Request) -> bool:
    if payload_mode == "sync":
        return False
    if payload_mode == "queued":
        return True
    return bool(getattr(request.app.state, "queue_enabled", False))


@router.post("/benchmarks/run", response_model=BenchmarkRunModel | RunDetail)
def run_benchmark(payload: BenchmarkRunRequest, request: Request) -> BenchmarkRunModel | RunDetail:
    if _use_queue(payload.mode, request):
        detail = _service(request).queue_benchmark(payload)
        queue = _queue(request)
        if queue is not None:
            queue.enqueue(detail.run_id, priority=payload.priority)
        return detail
    return BenchmarkRunModel(**_service(request).run_benchmark(payload).to_dict())


@router.get("/benchmarks", response_model=list[BenchmarkRunModel])
def list_benchmarks(request: Request) -> list[BenchmarkRunModel]:
    return [BenchmarkRunModel(**run.to_dict()) for run in _service(request).list_benchmark_runs()]


@router.get("/benchmarks/latest", response_model=BenchmarkRunModel)
def latest_benchmark(request: Request) -> BenchmarkRunModel:
    return BenchmarkRunModel(**_service(request).latest_benchmark_run().to_dict())


@router.get("/benchmarks/regressions", response_model=BenchmarkComparisonModel)
def latest_regressions(
    request: Request,
    threshold_percent: float = Query(default=10.0, ge=0.0),
) -> BenchmarkComparisonModel:
    return BenchmarkComparisonModel(**_service(request).latest_regressions(threshold_percent=threshold_percent).to_dict())


@router.get("/benchmarks/{benchmark_id}", response_model=BenchmarkRunModel)
def get_benchmark(benchmark_id: str, request: Request) -> BenchmarkRunModel:
    return BenchmarkRunModel(**_service(request).get_benchmark_run(benchmark_id).to_dict())


@router.post("/benchmarks/compare", response_model=BenchmarkComparisonModel)
def compare_benchmarks(payload: BenchmarkCompareRequest, request: Request) -> BenchmarkComparisonModel:
    return BenchmarkComparisonModel(**_service(request).compare(payload).to_dict())
