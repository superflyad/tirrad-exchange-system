from __future__ import annotations

import pytest

from sim.tes_models.events import parse_events
from sim.tes_simulation.strategy_metadata import (
    StrategyRunMetadata,
    build_strategy_run_metadata,
    strategy_metadata_to_dict,
)


def test_build_strategy_run_metadata_builds_metadata() -> None:
    events = parse_events(
        [
            {"type": "TradeExecuted", "data": {"price": 100, "qty": 1, "maker_order_id": 1, "taker_order_id": 2}},
            {"type": "OrderAccepted", "data": {"order_id": 3, "side": "BUY", "price": 99, "qty": 4}},
            {"type": "TradeExecuted", "data": {"price": 101, "qty": 2, "maker_order_id": 4, "taker_order_id": 5}},
        ]
    )

    metadata = build_strategy_run_metadata(strategy_name="mean_reversion", events=events, total_commands=7)

    assert metadata == StrategyRunMetadata(
        strategy_name="mean_reversion",
        total_commands=7,
        total_events=3,
        total_trades=2,
    )


def test_build_strategy_run_metadata_rejects_empty_strategy_name() -> None:
    events = parse_events([])

    with pytest.raises(ValueError, match="strategy_name must be a non-empty string"):
        build_strategy_run_metadata(strategy_name="", events=events, total_commands=0)


def test_build_strategy_run_metadata_rejects_negative_command_count() -> None:
    events = parse_events([])

    with pytest.raises(ValueError, match="total_commands must be >= 0"):
        build_strategy_run_metadata(strategy_name="trend", events=events, total_commands=-1)


def test_strategy_metadata_to_dict_output_is_stable() -> None:
    metadata = StrategyRunMetadata(
        strategy_name="breakout",
        total_commands=5,
        total_events=8,
        total_trades=3,
    )

    payload = strategy_metadata_to_dict(metadata)

    assert payload == {
        "strategy_name": "breakout",
        "total_commands": 5,
        "total_events": 8,
        "total_trades": 3,
    }
