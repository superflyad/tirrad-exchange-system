from __future__ import annotations

from typing import Any


def _event_types(events: list[dict[str, Any]]) -> list[str]:
    return [str(event.get("type")) for event in events]


def test_import_works() -> None:
    import tes_engine  # noqa: F401


def test_matching_engine_can_be_instantiated() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    assert engine is not None


def test_non_crossing_limit_order_returns_order_accepted() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    events = engine.place_limit_order(side="Bid", price_ticks=100, qty=10)

    assert "OrderAccepted" in _event_types(events)


def test_crossing_orders_produce_trade_executed() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    resting_events = engine.place_limit_order(side="Ask", price_ticks=100, qty=10)
    assert "OrderAccepted" in _event_types(resting_events)

    crossing_events = engine.place_limit_order(side="Bid", price_ticks=105, qty=5)
    assert "TradeExecuted" in _event_types(crossing_events)


def test_cancel_returns_order_canceled_for_accepted_order() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    accepted_events = engine.place_limit_order(side="Bid", price_ticks=100, qty=10)

    accepted = next(
        (event for event in accepted_events if event.get("type") == "OrderAccepted"),
        None,
    )
    assert accepted is not None

    cancel_events = engine.cancel(order_id=int(accepted["id"]))
    assert "OrderCanceled" in _event_types(cancel_events)
