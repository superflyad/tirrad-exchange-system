"""FastAPI application factory for the TES API service."""

from __future__ import annotations

from fastapi import FastAPI

from sim.api.errors import register_error_handlers
from sim.api.routes.health import router as health_router
from sim.api.routes.runs import router as runs_router
from sim.api.services.run_service import RunService
from sim.api.storage.in_memory import InMemoryRunStore


def create_app(store: InMemoryRunStore | None = None) -> FastAPI:
    """Create a configured TES FastAPI application."""

    app = FastAPI(
        title="Tirrad Exchange System API",
        version="0.1.0",
        description="Local API service for deterministic TES sessions and backtests.",
    )
    run_store = store or InMemoryRunStore()
    app.state.run_store = run_store
    app.state.run_service = RunService(run_store)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(runs_router)
    return app


app = create_app()
