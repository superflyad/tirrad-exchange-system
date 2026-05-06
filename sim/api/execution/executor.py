"""Execution adapter that runs queued TES API jobs from durable storage."""

from __future__ import annotations

from sim.api.models import RunDetail
from sim.api.services.run_service import RunService


class RunExecutor:
    """Execute a stored pending run by run identifier."""

    def __init__(self, run_service: RunService) -> None:
        self._run_service = run_service

    def execute(self, run_id: str) -> RunDetail:
        """Run the persisted session/backtest config and store artifacts."""

        return self._run_service.execute_pending_run(run_id)
