"""FastAPI application factory for the TES API service."""

from __future__ import annotations

from fastapi import FastAPI

from sim.api.errors import register_error_handlers
from sim.api.routes.health import router as health_router
from sim.api.routes.runs import router as runs_router
from sim.api.services.replay_service import ReplayService
from sim.api.services.run_service import RunService
from sim.api.storage import RunStore, create_run_store


def create_app(
    store: RunStore | None = None,
    *,
    store_kind: str | None = None,
    sqlite_path: str | None = None,
) -> FastAPI:
    """Create a configured TES FastAPI application."""

    app = FastAPI(
        title="Tirrad Exchange System API",
        version="0.1.0",
        description="Local API service for deterministic TES sessions and backtests.",
    )
    run_store = store or create_run_store(store=store_kind, sqlite_path=sqlite_path)
    app.state.run_store = run_store
    app.state.run_service = RunService(run_store)
    app.state.replay_service = ReplayService(run_store)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(runs_router)
    return app


app = create_app()
