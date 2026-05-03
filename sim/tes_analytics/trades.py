from __future__ import annotations

from sim.tes_models.events import TesEvent, TradeExecutedEvent


def _trade_events(events: list[TesEvent]) -> list[TradeExecutedEvent]:
    return [event for event in events if event.type == "TradeExecuted"]


def total_trades(events: list[TesEvent]) -> int:
    return len(_trade_events(events))


def total_traded_qty(events: list[TesEvent]) -> int:
    return sum(event.data.qty for event in _trade_events(events))


def traded_notional(events: list[TesEvent]) -> int:
    return sum(event.data.price * event.data.qty for event in _trade_events(events))


def average_trade_price(events: list[TesEvent]) -> float:
    qty = total_traded_qty(events)
    if qty == 0:
        return 0.0
    return traded_notional(events) / qty
