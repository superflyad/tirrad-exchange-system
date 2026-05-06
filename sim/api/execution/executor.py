"""Execution adapter that runs queued TES API jobs from durable storage."""

from __future__ import annotations

from sim.api.models import RunDetail
from sim.api.services.benchmark_service import BenchmarkService
from sim.api.services.run_service import RunService


class RunExecutor:
    """Execute a stored pending run by run identifier."""

    def __init__(self, run_service: RunService, benchmark_service: BenchmarkService | None = None) -> None:
        self._run_service = run_service
        self._benchmark_service = benchmark_service

    def execute(self, run_id: str) -> RunDetail:
        """Run the persisted session/backtest config and store artifacts."""

        record = self._run_service._store.get_run(run_id)  # noqa: SLF001 - executor dispatches by persisted type.
        if record is not None and record.run_type == "benchmark":
            if self._benchmark_service is None:
                raise RuntimeError("benchmark service is not configured")
            return self._benchmark_service.execute_pending_run(run_id)
        return self._run_service.execute_pending_run(run_id)
