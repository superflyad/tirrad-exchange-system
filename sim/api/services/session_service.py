"""Session execution service for the TES API."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sim.api.errors import InvalidRequestError
from sim.api.models import SessionRunRequest


def run_session(
    request: SessionRunRequest,
    *,
    run_id: str | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    """Execute a market session and return JSON-friendly artifacts."""

    from sim.session.models import MarketSessionConfig
    from sim.session.scenarios import get_market_scenario

    try:
        get_market_scenario(request.scenario)
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc

    config = MarketSessionConfig(
        scenario=request.scenario,
        steps=request.steps,
        symbols=tuple(request.symbols),
        seed=request.seed,
        initial_price=request.initial_price,
        volatility=request.volatility,
        spread_width=max(1, int(round(request.initial_price * 0.001))),
        min_order_size=1,
        max_order_size=10,
        probability_market_order=0.35,
        probability_cancel_replace=0.1,
        participant_count=request.participants,
        depth_levels=request.depth_levels,
    )
    from sim.session.runner import MarketSessionRunner

    result = MarketSessionRunner(config).run(
        progress_interval=request.progress_interval,
        progress_callback=progress_callback,
        verbose=request.stream_events or request.stream_snapshots,
    )
    report = asdict(result.report)
    accounts = [
        {
            "initial_cash": request.initial_cash,
            "cash": request.initial_cash + report["realized_pnl"],
            "positions": {},
            "mark_to_market": dict(result.report.per_symbol_pnl),
            "equity": request.initial_cash + report["final_equity"],
        }
    ]
    return {
        "config": result.to_dict()["config"] | {"initial_cash": request.initial_cash},
        "report": report,
        "events": result.events,
        "snapshots": result.snapshots,
        "accounts": accounts,
    }
