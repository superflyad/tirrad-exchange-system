from __future__ import annotations

from sim.tes_models.events import parse_events


def test_import_works() -> None:
    import tes_engine  # noqa: F401


def test_matching_engine_can_be_instantiated() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    assert engine is not None


def test_non_crossing_limit_order_returns_order_accepted() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    raw_events = engine.place_limit_order(side="Bid", price_ticks=100, qty=10)
    events = parse_events(raw_events)

    assert any(event.type == "OrderAccepted" for event in events)


def test_crossing_orders_produce_trade_executed() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    resting_raw = engine.place_limit_order(side="Ask", price_ticks=100, qty=10)
    resting_events = parse_events(resting_raw)
    assert any(event.type == "OrderAccepted" for event in resting_events)

    crossing_raw = engine.place_limit_order(side="Bid", price_ticks=105, qty=5)
    crossing_events = parse_events(crossing_raw)
    trade_events = [event for event in crossing_events if event.type == "TradeExecuted"]

    assert trade_events
    assert trade_events[0].data.price == 100
    assert trade_events[0].data.qty == 5


def test_cancel_returns_order_canceled_for_accepted_order() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    accepted_raw = engine.place_limit_order(side="Bid", price_ticks=100, qty=10)
    accepted_events = parse_events(accepted_raw)

    accepted = next((event for event in accepted_events if event.type == "OrderAccepted"), None)
    assert accepted is not None

    cancel_raw = engine.cancel(order_id=accepted.data.order_id)
    cancel_events = parse_events(cancel_raw)
    assert any(event.type == "OrderCanceled" for event in cancel_events)
