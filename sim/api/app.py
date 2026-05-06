"""FastAPI application factory for the TES API service."""

from __future__ import annotations

import os

from fastapi import FastAPI

from sim.api.errors import register_error_handlers
from sim.api.execution.queue import SQLiteRunQueue
from sim.api.execution.scheduler import SchedulerService
from sim.api.routes.benchmarks import router as benchmarks_router
from sim.api.routes.health import router as health_router
from sim.api.routes.runs import router as runs_router
from sim.api.routes.scheduler import router as scheduler_router
from sim.api.routes.tournaments import router as tournaments_router
from sim.api.services.benchmark_service import BenchmarkService
from sim.api.services.replay_service import ReplayService
from sim.api.services.run_service import RunService
from sim.api.services.stream_service import StreamService
from sim.api.services.tournament_service import TournamentService
from sim.api.storage import DEFAULT_SQLITE_PATH, RunStore, create_run_store


def create_app(
    store: RunStore | None = None,
    *,
    store_kind: str | None = None,
    sqlite_path: str | None = None,
    queue_enabled: bool | None = None,
) -> FastAPI:
    """Create a configured TES FastAPI application."""

    app = FastAPI(
        title="Tirrad Exchange System API",
        version="0.1.0",
        description="Local API service for deterministic TES sessions and backtests.",
    )
    run_store = store or create_run_store(store=store_kind, sqlite_path=sqlite_path)
    stream_service = StreamService(run_store)
    enabled = _queue_enabled(queue_enabled)
    queue_path = sqlite_path or os.environ.get("TES_SQLITE_PATH") or str(DEFAULT_SQLITE_PATH)
    app.state.run_store = run_store
    app.state.stream_service = stream_service
    app.state.run_service = RunService(run_store, stream_service)
    app.state.replay_service = ReplayService(run_store)
    app.state.benchmark_service = BenchmarkService(run_store)
    app.state.queue_enabled = enabled
    app.state.run_queue = SQLiteRunQueue(queue_path) if enabled else None
    app.state.scheduler_service = SchedulerService(app.state.run_queue) if app.state.run_queue is not None else None
    app.state.tournament_service = TournamentService(run_store, app.state.run_service, app.state.run_queue)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(benchmarks_router)
    app.include_router(runs_router)
    app.include_router(scheduler_router)
    app.include_router(tournaments_router)
    return app


def _queue_enabled(value: bool | None) -> bool:
    if value is not None:
        return value
    raw = os.environ.get("TES_QUEUE_ENABLED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


app = create_app()
