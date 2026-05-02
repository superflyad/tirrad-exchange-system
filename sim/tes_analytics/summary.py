from __future__ import annotations

from sim.tes_models.events import TesEvent


def count_events(events: list[TesEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.type] = counts.get(event.type, 0) + 1
    return counts


def count_trades(events: list[TesEvent]) -> int:
    return sum(1 for event in events if event.type == "TradeExecuted")


def total_traded_qty(events: list[TesEvent]) -> int:
    return sum(event.data.qty for event in events if event.type == "TradeExecuted")


def traded_notional(events: list[TesEvent]) -> int:
    return sum(event.data.price * event.data.qty for event in events if event.type == "TradeExecuted")
