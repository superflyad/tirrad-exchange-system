from __future__ import annotations

from sim.tes_models.events import (
    OrderAcceptedData,
    OrderAcceptedEvent,
    OrderCanceledData,
    OrderCanceledEvent,
    TesEvent,
    TopOfBookData,
    TopOfBookEvent,
    TradeExecutedData,
    TradeExecutedEvent,
)
from sim.tes_replay import ReplayResult, replay_events


def test_replay_empty_event_list() -> None:
    events: list[TesEvent] = []

    result = replay_events(events)

    assert result == ReplayResult(events=[], total_events=0, total_trades=0)
    assert result.events is not events


def test_replay_preserves_event_order() -> None:
    events: list[TesEvent] = [
        OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=3)),
        TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(price=101, qty=2, maker_order_id=1, taker_order_id=2),
        ),
        TopOfBookEvent(type="TopOfBook", data=TopOfBookData(best_bid=100, best_ask=102)),
        OrderCanceledEvent(type="OrderCanceled", data=OrderCanceledData(order_id=1)),
    ]

    result = replay_events(events)

    assert result.events == events
    assert result.events is not events
    assert result.total_events == 4
    assert result.total_trades == 1


def test_replay_counts_multiple_trade_events() -> None:
    events: list[TesEvent] = [
        TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(price=100, qty=5, maker_order_id=10, taker_order_id=20),
        ),
        TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(price=99, qty=1, maker_order_id=11, taker_order_id=21),
        ),
        OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=2, side="SELL", price=103, qty=4)),
    ]

    result = replay_events(events)

    assert result.total_events == 3
    assert result.total_trades == 2
