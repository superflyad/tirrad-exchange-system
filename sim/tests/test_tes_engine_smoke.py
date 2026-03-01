from __future__ import annotations


def test_trade_executed_event_emitted() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()

    resting_events = engine.place_limit_order(side="Ask", price_ticks=100, qty=10)
    assert any(event["type"] == "OrderAccepted" for event in resting_events)

    crossing_events = engine.place_limit_order(side="Bid", price_ticks=105, qty=5)
    assert any(event["type"] == "TradeExecuted" for event in crossing_events)
