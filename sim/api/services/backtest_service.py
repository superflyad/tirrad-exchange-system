"""Backtest execution service for the TES API."""

from __future__ import annotations

from dataclasses import asdict
from importlib import import_module
from typing import Any

from sim.api.errors import InvalidRequestError
from sim.api.models import BacktestRunRequest
from sim.backtest import BacktestConfig, BacktestRunner
from sim.tes_serialization.events import serialize_events
from sim.tes_strategy.registry import get_strategy


def _step_to_dict(step: object) -> dict[str, Any]:
    raw = asdict(step)
    raw["events"] = serialize_events(step.events)
    return raw


def run_backtest(
    request: BacktestRunRequest,
    *,
    run_id: str | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    """Execute a strategy backtest and return JSON-friendly artifacts."""

    try:
        strategy = get_strategy(request.strategy)
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc

    tes_engine = import_module("tes_engine")
    engine = tes_engine.MatchingEngine()
    config = BacktestConfig(
        strategy_names=[request.strategy],
        symbols=list(request.symbols),
        initial_cash=request.initial_cash,
        depth_levels=request.depth_levels,
    )
    result = BacktestRunner(engine=engine, config=config, strategies=[strategy]).run(
        progress_interval=request.progress_interval,
        progress_callback=progress_callback,
    )
    return {
        "config": asdict(result.config),
        "report": asdict(result.metrics),
        "events": serialize_events(result.events),
        "snapshots": [{"step": index + 1, "symbols": snapshot} for index, snapshot in enumerate(result.snapshots)],
        "accounts": [dict(account) for account in result.account_states],
        "steps": [_step_to_dict(step) for step in result.steps],
    }
