from __future__ import annotations

from sim.tes_models.events import parse_events


def test_non_crossing_limit_order_contract() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    raw_events = engine.place_limit_order(side="Bid", price_ticks=100, qty=10)
    events = parse_events(raw_events)
    assert any(event.type == "OrderAccepted" for event in events)


def test_crossing_orders_contract_trade_present() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.place_limit_order(side="Ask", price_ticks=100, qty=10)
    raw_events = engine.place_limit_order(side="Bid", price_ticks=100, qty=5)
    events = parse_events(raw_events)
    assert any(event.type == "TradeExecuted" for event in events)


def test_cancel_contract_order_canceled_present() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    accepted_events = parse_events(engine.place_limit_order(side="Bid", price_ticks=100, qty=10))
    accepted = next(event for event in accepted_events if event.type == "OrderAccepted")

    cancel_events = parse_events(engine.cancel(order_id=accepted.data.order_id))
    assert any(event.type == "OrderCanceled" for event in cancel_events)


def test_binding_events_have_no_extra_top_level_keys() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    raw_events = engine.place_limit_order(side="Bid", price_ticks=100, qty=10)

    for raw in raw_events:
        assert set(raw.keys()) == {"type", "data"}
