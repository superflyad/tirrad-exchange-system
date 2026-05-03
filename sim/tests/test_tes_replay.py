from __future__ import annotations

from sim.tes_models.events import (
    OrderAcceptedData,
    OrderAccepted,
    OrderCanceledData,
    OrderCanceled,
    TesEngineEvent,
    TopOfBookData,
    TopOfBook,
    TradeExecutedData,
    TradeExecuted,
)
from sim.tes_replay import ReplayResult, replay_events


def test_replay_empty_event_list() -> None:
    events: list[TesEngineEvent] = []

    result = replay_events(events)

    assert result == ReplayResult(events=[], total_events=0, total_trades=0)
    assert result.events is not events


def test_replay_preserves_event_order() -> None:
    events: list[TesEngineEvent] = [
        OrderAccepted(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=3)),
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=101, qty=2, maker_order_id=1, taker_order_id=2),
        ),
        TopOfBook(type="TopOfBook", data=TopOfBookData(best_bid=100, best_ask=102)),
        OrderCanceled(type="OrderCanceled", data=OrderCanceledData(order_id=1)),
    ]

    result = replay_events(events)

    assert result.events == events
    assert result.events is not events
    assert result.total_events == 4
    assert result.total_trades == 1


def test_replay_counts_multiple_trade_events() -> None:
    events: list[TesEngineEvent] = [
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=100, qty=5, maker_order_id=10, taker_order_id=20),
        ),
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=99, qty=1, maker_order_id=11, taker_order_id=21),
        ),
        OrderAccepted(type="OrderAccepted", data=OrderAcceptedData(order_id=2, side="SELL", price=103, qty=4)),
    ]

    result = replay_events(events)

    assert result.total_events == 3
    assert result.total_trades == 2
