from __future__ import annotations

import pytest

from sim.tes_models.events import parse_events
from sim.tes_simulation.results import build_run_record


def test_build_run_record_counts_trades() -> None:
    events = parse_events(
        [
            {"type": "TradeExecuted", "data": {"price": 100, "qty": 1, "maker_order_id": 1, "taker_order_id": 2}},
            {"type": "TradeExecuted", "data": {"price": 101, "qty": 2, "maker_order_id": 3, "taker_order_id": 4}},
        ]
    )

    record = build_run_record(run_id="run-1", events=events, total_commands=2)

    assert record.summary.total_trades == 2


def test_build_run_record_counts_accepted_orders() -> None:
    events = parse_events(
        [
            {"type": "OrderAccepted", "data": {"order_id": 1, "side": "BUY", "price": 100, "qty": 5}},
            {"type": "OrderAccepted", "data": {"order_id": 2, "side": "SELL", "price": 101, "qty": 3}},
        ]
    )

    record = build_run_record(run_id="run-2", events=events, total_commands=2)

    assert record.summary.total_order_accepted == 2


def test_build_run_record_counts_canceled_orders() -> None:
    events = parse_events(
        [
            {"type": "OrderCanceled", "data": {"order_id": 1}},
            {"type": "OrderCanceled", "data": {"order_id": 2}},
        ]
    )

    record = build_run_record(run_id="run-3", events=events, total_commands=2)

    assert record.summary.total_order_canceled == 2


def test_build_run_record_stores_run_id() -> None:
    events = parse_events([])

    record = build_run_record(run_id="tes-run-123", events=events, total_commands=0)

    assert record.run_id == "tes-run-123"


def test_build_run_record_rejects_empty_run_id() -> None:
    events = parse_events([])

    with pytest.raises(ValueError):
        build_run_record(run_id="", events=events, total_commands=0)


def test_build_run_record_rejects_negative_command_count() -> None:
    events = parse_events([])

    with pytest.raises(ValueError):
        build_run_record(run_id="run-4", events=events, total_commands=-1)
