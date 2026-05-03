from __future__ import annotations

from sim.tes_analytics.trades import average_trade_price, total_traded_qty, total_trades, traded_notional
from sim.tes_models.events import OrderAcceptedData, OrderAcceptedEvent, TesEvent, TradeExecutedData, TradeExecutedEvent


def test_trade_metrics_empty_events() -> None:
    events: list[TesEvent] = []

    assert total_trades(events) == 0
    assert total_traded_qty(events) == 0
    assert traded_notional(events) == 0
    assert average_trade_price(events) == 0.0


def test_trade_metrics_single_trade() -> None:
    events: list[TesEvent] = [
        TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(price=100, qty=5, maker_order_id=10, taker_order_id=20),
        )
    ]

    assert total_trades(events) == 1
    assert total_traded_qty(events) == 5
    assert traded_notional(events) == 500
    assert average_trade_price(events) == 100.0


def test_trade_metrics_multiple_trades_aggregated() -> None:
    events: list[TesEvent] = [
        OrderAcceptedEvent(type="OrderAccepted", data=OrderAcceptedData(order_id=1, side="BUY", price=100, qty=3)),
        TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(price=100, qty=5, maker_order_id=10, taker_order_id=20),
        ),
        TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(price=95, qty=4, maker_order_id=11, taker_order_id=21),
        ),
        TradeExecutedEvent(
            type="TradeExecuted",
            data=TradeExecutedData(price=110, qty=1, maker_order_id=12, taker_order_id=22),
        ),
    ]

    assert total_trades(events) == 3
    assert total_traded_qty(events) == 10
    assert traded_notional(events) == 990
    assert average_trade_price(events) == 99.0
