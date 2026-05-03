from __future__ import annotations

from sim.tes_analytics import count_events, count_trades, total_traded_qty, traded_notional
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


def test_empty_events() -> None:
    events: list[TesEngineEvent] = []

    assert count_events(events) == {}
    assert count_trades(events) == 0
    assert total_traded_qty(events) == 0
    assert traded_notional(events) == 0


def test_accepted_only_events() -> None:
    events: list[TesEngineEvent] = [
        OrderAccepted(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=3)),
        OrderAccepted(type="OrderAccepted", data=OrderAcceptedData(order_id=2, side="SELL", price=101, qty=4)),
    ]

    assert count_events(events) == {"OrderAccepted": 2}
    assert count_trades(events) == 0
    assert total_traded_qty(events) == 0
    assert traded_notional(events) == 0


def test_one_trade() -> None:
    events: list[TesEngineEvent] = [
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=100, qty=5, maker_order_id=10, taker_order_id=20),
        )
    ]

    assert count_events(events) == {"TradeExecuted": 1}
    assert count_trades(events) == 1
    assert total_traded_qty(events) == 5
    assert traded_notional(events) == 500


def test_multiple_trades() -> None:
    events: list[TesEngineEvent] = [
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=100, qty=5, maker_order_id=10, taker_order_id=20),
        ),
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=95, qty=4, maker_order_id=11, taker_order_id=21),
        ),
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=110, qty=1, maker_order_id=12, taker_order_id=22),
        ),
    ]

    assert count_events(events) == {"TradeExecuted": 3}
    assert count_trades(events) == 3
    assert total_traded_qty(events) == 10
    assert traded_notional(events) == 990


def test_mixed_event_types() -> None:
    events: list[TesEngineEvent] = [
        OrderAccepted(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=3)),
        TopOfBook(type="TopOfBook", data=TopOfBookData(best_bid=99, best_ask=101)),
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=101, qty=2, maker_order_id=1, taker_order_id=2),
        ),
        OrderCanceled(type="OrderCanceled", data=OrderCanceledData(order_id=1)),
        TradeExecuted(
            type="TradeExecuted",
            data=TradeExecutedData(price=102, qty=3, maker_order_id=3, taker_order_id=4),
        ),
    ]

    assert count_events(events) == {
        "OrderAccepted": 1,
        "TopOfBook": 1,
        "TradeExecuted": 2,
        "OrderCanceled": 1,
    }
    assert count_trades(events) == 2
    assert total_traded_qty(events) == 5
    assert traded_notional(events) == 508
