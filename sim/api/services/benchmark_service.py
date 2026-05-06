"""Benchmark orchestration and regression reporting for the TES API."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sim.api.errors import InvalidRequestError, RunNotFoundError
from sim.api.models import BenchmarkCompareRequest, BenchmarkRunRequest, RunDetail
from sim.api.storage import RunRecord, RunStore
from sim.tes_benchmarks.models import BenchmarkComparison, BenchmarkRun, BenchmarkScenario, compare_benchmark_runs
from sim.tes_benchmarks.runner import machine_info, run_engine_benchmark


class BenchmarkService:
    """Coordinates benchmark execution, storage, and comparisons."""

    def __init__(self, store: RunStore) -> None:
        self._store = store

    def queue_benchmark(self, request: BenchmarkRunRequest) -> RunDetail:
        record = self._store.create_run(run_type="benchmark", config=request.model_dump(exclude={"mode"}))
        return _run_detail(record)

    def run_benchmark(self, request: BenchmarkRunRequest) -> BenchmarkRun:
        benchmark = self._execute_benchmark(config=request.model_dump(exclude={"mode"}))
        if request.persist:
            return self._store.store_benchmark_run(benchmark)
        return benchmark

    def execute_pending_run(self, run_id: str) -> RunDetail:
        record = self._store.get_run(run_id)
        if record is None:
            raise RunNotFoundError(run_id)
        if record.run_type != "benchmark":
            raise InvalidRequestError(f"unsupported benchmark run type: {record.run_type}")
        if record.status == "completed":
            raise InvalidRequestError(f"run is already completed: {run_id}")
        self._store.update_run(run_id, status="running", started_at=datetime.now(UTC))
        try:
            benchmark = self._execute_benchmark(config=record.config)
            stored = self._store.store_benchmark_run(benchmark)
            self._store.store_result(
                run_id,
                report=stored.to_dict(),
                events=[],
                snapshots=[],
                accounts=[],
                logs=[{"level": "info", "message": "benchmark completed", "benchmark_id": stored.benchmark_id}],
            )
            completed = self._store.update_run(run_id, status="completed", completed_at=datetime.now(UTC))
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            self._store.update_run(run_id, status="failed", completed_at=datetime.now(UTC), error=message)
            raise
        if completed is None:
            raise RunNotFoundError(run_id)
        return _run_detail(completed)

    def list_benchmark_runs(self) -> list[BenchmarkRun]:
        return self._store.list_benchmark_runs()

    def latest_benchmark_run(self) -> BenchmarkRun:
        runs = self._store.list_benchmark_runs()
        if not runs:
            raise RunNotFoundError("latest benchmark")
        return runs[-1]

    def get_benchmark_run(self, benchmark_id: str) -> BenchmarkRun:
        run = self._store.get_benchmark_run(benchmark_id)
        if run is None:
            raise RunNotFoundError(benchmark_id)
        return run

    def compare(self, request: BenchmarkCompareRequest) -> BenchmarkComparison:
        runs = self._store.list_benchmark_runs()
        baseline_id = request.baseline_id
        candidate_id = request.candidate_id
        if baseline_id is None or candidate_id is None:
            if len(runs) < 2:
                raise InvalidRequestError("at least two benchmark runs are required for latest comparison")
            baseline_id = baseline_id or runs[-2].benchmark_id
            candidate_id = candidate_id or runs[-1].benchmark_id
        comparison = self._store.compare_benchmark_runs(
            baseline_id,
            candidate_id,
            threshold_percent=request.threshold_percent,
        )
        if comparison is None:
            raise RunNotFoundError(f"{baseline_id} or {candidate_id}")
        return comparison

    def latest_regressions(self, *, threshold_percent: float = 10.0) -> BenchmarkComparison:
        runs = self._store.list_benchmark_runs()
        if len(runs) < 2:
            raise InvalidRequestError("at least two benchmark runs are required for regression comparison")
        return compare_benchmark_runs(runs[-2], runs[-1], threshold_percent=threshold_percent)

    def _execute_benchmark(self, *, config: dict[str, Any]) -> BenchmarkRun:
        executable = _default_benchmark_executable()
        if executable.exists():
            benchmark, _human = run_engine_benchmark(executable=executable, repo_root=_repo_root(), config=config)
            return benchmark
        return _fallback_benchmark(config=config)


def _default_benchmark_executable() -> Path:
    return _repo_root() / "out" / "build" / "debug-ninja" / "engine" / "tes_engine_bench"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _fallback_benchmark(*, config: dict[str, Any]) -> BenchmarkRun:
    start = time.perf_counter()
    operations = 10_000
    total = 0
    for value in range(operations):
        total += value
    elapsed = max(time.perf_counter() - start, 0.000001)
    return BenchmarkRun.create(
        scenarios=[
            BenchmarkScenario(
                name="api_python_smoke",
                operation_count=operations,
                elapsed_ms=elapsed * 1000.0,
                ops_per_sec=operations / elapsed,
                notes=f"fallback_total={total}",
            )
        ],
        git_sha=None,
        machine=machine_info(),
        notes="C++ benchmark executable was not available; API fallback smoke benchmark was used.",
        config=config,
    )


def _run_detail(record: RunRecord) -> RunDetail:
    return RunDetail(
        run_id=record.run_id,
        run_type=record.run_type,
        status=record.status,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        config=record.config,
        report_summary={
            "benchmark_id": record.report.get("benchmark_id"),
            "scenario_count": len(record.report.get("scenarios", [])) if isinstance(record.report, dict) else 0,
        },
        error=record.error,
        polling_url=f"/runs/{record.run_id}",
        stream_url=None,
        report=record.report,
    )
