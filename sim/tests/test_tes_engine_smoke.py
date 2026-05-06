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


def test_python_stop_order_smoke() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.place_limit_order("Bid", 99, 10, symbol="AAA")
    engine.place_limit_order("Ask", 101, 10, symbol="AAA")

    accepted = engine.place_stop_order("Bid", 101, 2, symbol="AAA")
    assert accepted[0]["type"] == "StopOrderAccepted"
    assert accepted[0]["data"]["symbol"] == "AAA"

    events = engine.place_limit_order("Bid", 101, 3, symbol="AAA")
    assert any(event["type"] == "StopOrderTriggered" for event in events)
    assert any(event["type"] == "TradeExecuted" for event in events)


def test_python_auction_phase_and_indicative_apis() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    events = engine.set_trading_phase("AUC", "OpeningAuction")
    assert engine.trading_phase("AUC") == "OpeningAuction"
    assert events[0]["type"] == "AuctionStarted"

    engine.place_limit_order("Ask", 100, 5, symbol="AUC")
    engine.place_limit_order("Bid", 105, 3, symbol="AUC")

    assert engine.indicative_price("AUC") == 100
    assert engine.indicative_volume("AUC") == 3
    assert engine.auction_imbalance("AUC") == -2


def test_python_auction_flow_smoke() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.set_trading_phase("AUC", "OpeningAuction")
    buy_events = engine.place_limit_order("Bid", 105, 3, symbol="AUC")
    sell_events = engine.place_limit_order("Ask", 100, 3, symbol="AUC")
    assert not any(event["type"] == "TradeExecuted" for event in buy_events + sell_events)

    uncross_events = parse_events(engine.uncross("AUC"))
    assert any(event.type == "AuctionUncross" for event in uncross_events)
    assert any(event.type == "TradeExecuted" for event in uncross_events)
    assert engine.trading_phase("AUC") == "Continuous"


def test_hidden_order_api_smoke_and_depth_excludes_hidden() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    raw_events = engine.place_hidden_order(side="Ask", price_ticks=100, qty=5, symbol="HID")
    events = parse_events(raw_events)

    assert events[0].type == "HiddenOrderAccepted"
    assert engine.depth(1, "HID")["asks"] == []

    trade_events = parse_events(engine.place_limit_order(side="Bid", price_ticks=100, qty=2, symbol="HID"))
    assert any(event.type == "TradeExecuted" for event in trade_events)


def test_iceberg_order_api_smoke_and_depth_shows_visible_only() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    raw_events = engine.place_iceberg_order(side="Ask", price_ticks=101, total_qty=7, display_qty=3, symbol="ICE")
    events = parse_events(raw_events)

    assert events[0].type == "IcebergOrderAccepted"
    assert events[0].data.current_visible_qty == 3
    depth = engine.depth(1, "ICE")
    assert depth["asks"] == [{"price": 101, "qty": 3}]

    fill_events = parse_events(engine.place_limit_order(side="Bid", price_ticks=101, qty=3, symbol="ICE"))
    assert any(event.type == "IcebergReplenished" for event in fill_events)
    assert engine.depth(1, "ICE")["asks"] == [{"price": 101, "qty": 3}]
