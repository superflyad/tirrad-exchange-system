from __future__ import annotations

import pytest

from sim.tes_engine_adapter import execute_command, execute_commands
from sim.tes_models.commands import CancelOrderCommand, LimitOrderCommand, MarketOrderCommand, ReplaceOrderCommand


def test_execute_limit_order_command_returns_models() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    command = LimitOrderCommand(side="BUY", price=100, qty=10)

    events = execute_command(engine, command)

    assert any(event.type == "OrderAccepted" for event in events)


def test_non_crossing_limit_order_includes_order_accepted() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=10))

    assert any(event.type == "OrderAccepted" for event in events)


def test_crossing_two_limit_orders_produces_trade_executed() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=10))
    events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=5))

    assert any(event.type == "TradeExecuted" for event in events)
    assert any(event.type == "OrderFilled" for event in events)


def test_cancel_command_produces_order_canceled() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    accepted_events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=10))
    accepted = next(event for event in accepted_events if event.type == "OrderAccepted")

    cancel_events = execute_command(engine, CancelOrderCommand(order_id=accepted.data.order_id))

    assert any(event.type == "OrderCanceled" for event in cancel_events)


def test_execute_commands_aggregates_events() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    commands = [
        LimitOrderCommand(side="SELL", price=100, qty=10),
        LimitOrderCommand(side="BUY", price=100, qty=5),
    ]
    events = execute_commands(engine, commands)

    assert any(event.type == "OrderAccepted" for event in events)
    assert any(event.type == "TradeExecuted" for event in events)


def test_execute_command_rejects_unknown_command_type() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()

    with pytest.raises(TypeError):
        execute_command(engine, object())  # type: ignore[arg-type]


def test_invalid_limit_order_produces_order_rejected() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    events = execute_command(engine, LimitOrderCommand(side="BUY", price=-1, qty=10))

    rejected = next(event for event in events if event.type == "OrderRejected")
    assert rejected.data.reason == "InvalidPrice"


def test_cancel_unknown_order_produces_cancel_rejected() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    events = execute_command(engine, CancelOrderCommand(order_id=999))

    rejected = next(event for event in events if event.type == "CancelRejected")
    assert rejected.data.reason == "UnknownOrderId"


def test_market_order_command_produces_trade_executed() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=10))

    events = execute_command(engine, MarketOrderCommand(side="BUY", qty=5))

    assert any(event.type == "TradeExecuted" for event in events)


def test_ioc_partial_fill_cancels_remainder() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=3))

    events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=5, time_in_force="IOC"))

    assert any(event.type == "TradeExecuted" for event in events)
    assert any(event.type == "OrderExpired" for event in events)


def test_fok_failure_cancels_order_without_trade() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=3))

    events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=5, time_in_force="FOK"))

    assert any(event.type == "OrderExpired" for event in events)
    assert not any(event.type == "TradeExecuted" for event in events)


def test_market_rejection_is_parsed_with_no_liquidity_reason() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    events = execute_command(engine, MarketOrderCommand(side="BUY", qty=5))

    rejected = next(event for event in events if event.type == "OrderRejected")
    assert rejected.data.reason == "NoLiquidity"


def test_ioc_no_fill_expires_without_resting() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=105, qty=2))

    events = execute_command(engine, LimitOrderCommand(side="BUY", price=104, qty=2, time_in_force="IOC"))

    assert [event.type for event in events] == ["OrderExpired"]
    depth = engine.depth(5)
    assert depth["bids"] == []
    assert len(depth["asks"]) == 1
    assert depth["asks"][0]["price"] == 105
    assert depth["asks"][0]["qty"] == 2


def test_fok_can_fully_fill_across_price_levels() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=3))
    execute_command(engine, LimitOrderCommand(side="SELL", price=101, qty=2))

    events = execute_command(engine, LimitOrderCommand(side="BUY", price=101, qty=5, time_in_force="FOK"))

    trades = [event for event in events if event.type == "TradeExecuted"]
    assert len(trades) == 2
    assert trades[0].data.price == 100
    assert trades[1].data.price == 101
    depth = engine.depth(5)
    assert depth["asks"] == []


def test_fok_insufficient_qty_does_not_mutate_book() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=4))

    events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=5, time_in_force="FOK"))

    assert [event.type for event in events] == ["OrderExpired"]
    depth = engine.depth(5)
    assert depth["bids"] == []
    assert len(depth["asks"]) == 1
    assert depth["asks"][0]["price"] == 100
    assert depth["asks"][0]["qty"] == 4


def test_fok_respects_limit_price_and_does_not_cross_higher_level() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=3))
    execute_command(engine, LimitOrderCommand(side="SELL", price=101, qty=3))

    events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=5, time_in_force="FOK"))

    assert [event.type for event in events] == ["OrderExpired"]
    depth = engine.depth(5)
    assert len(depth["asks"]) == 2
    assert depth["asks"][0]["price"] == 100
    assert depth["asks"][0]["qty"] == 3
    assert depth["asks"][1]["price"] == 101
    assert depth["asks"][1]["qty"] == 3


def test_market_buy_sweeps_lowest_ask_first_and_never_rests() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=101, qty=2))
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=3))
    execute_command(engine, LimitOrderCommand(side="SELL", price=102, qty=4))

    events = execute_command(engine, MarketOrderCommand(side="BUY", qty=7))

    trades = [event for event in events if event.type == "TradeExecuted"]
    assert [trade.data.price for trade in trades] == [100, 101, 102]
    assert [trade.data.qty for trade in trades] == [3, 2, 2]
    assert not any(event.type == "OrderAccepted" for event in events)


def test_market_sell_sweeps_highest_bid_first_and_never_rests() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="BUY", price=99, qty=2))
    execute_command(engine, LimitOrderCommand(side="BUY", price=101, qty=3))
    execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=4))

    events = execute_command(engine, MarketOrderCommand(side="SELL", qty=8))

    trades = [event for event in events if event.type == "TradeExecuted"]
    assert [trade.data.price for trade in trades] == [101, 100, 99]
    assert [trade.data.qty for trade in trades] == [3, 4, 1]
    assert not any(event.type == "OrderAccepted" for event in events)


def test_partial_market_fill_emits_trade_and_lifecycle_events() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=3))
    execute_command(engine, LimitOrderCommand(side="SELL", price=101, qty=3))

    events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=4, time_in_force="FOK"))

    assert [event.type for event in events] == ["OrderExpired"]
    depth = engine.depth(5)
    assert len(depth["asks"]) == 2
    assert depth["asks"][0]["price"] == 100
    assert depth["asks"][0]["qty"] == 3
    assert depth["asks"][1]["price"] == 101
    assert depth["asks"][1]["qty"] == 3

    events = execute_command(engine, MarketOrderCommand(side="BUY", qty=5))

    assert [event.type for event in events] == [
        "TradeExecuted",
        "OrderPartiallyFilled",
        "TopOfBook",
        "TradeExecuted",
        "OrderFilled",
    ]
    first_trade = events[0]
    partial = events[1]
    second_trade = events[3]
    assert first_trade.data.price == 100
    assert first_trade.data.qty == 3
    assert partial.data.last_fill_qty == 3
    assert partial.data.remaining_qty == 2
    assert second_trade.data.price == 101
    assert second_trade.data.qty == 2



def test_replace_order_command_produces_lifecycle_events() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    accepted_events = execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=10))
    accepted = next(event for event in accepted_events if event.type == "OrderAccepted")

    replace_events = execute_command(engine, ReplaceOrderCommand(order_id=accepted.data.order_id, price=101, qty=5))

    assert any(event.type == "OrderCanceled" for event in replace_events)
    assert any(event.type == "OrderAccepted" for event in replace_events)


def test_replace_unknown_order_produces_cancel_rejected() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    events = execute_command(engine, ReplaceOrderCommand(order_id=999, price=101, qty=5))

    rejected = next(event for event in events if event.type == "CancelRejected")
    assert rejected.data.reason == "UnknownOrderId"


def test_symbol_aware_orders_depth_and_events_are_isolated() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    accepted = execute_command(engine, LimitOrderCommand(side="SELL", price=100, qty=3, symbol="AAA"))
    execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=3, symbol="BBB"))

    assert any(event.type == "OrderAccepted" and event.data.symbol == "AAA" for event in accepted)
    assert len(engine.depth(5, "AAA")["asks"]) == 1
    assert len(engine.depth(5, "BBB")["bids"]) == 1
    assert engine.depth(5, "AAA")["bids"] == []
    assert engine.depth(5, "BBB")["asks"] == []

    trades = execute_command(engine, MarketOrderCommand(side="BUY", qty=2, symbol="AAA"))

    assert any(event.type == "TradeExecuted" and event.data.symbol == "AAA" for event in trades)
    assert len(engine.depth(5, "BBB")["bids"]) == 1


def test_adapter_passes_default_symbol_explicitly_to_limit_and_market_calls() -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.calls: list[tuple[object, ...]] = []

        def place_limit_order(
            self, side: str, price: int, qty: int, time_in_force: str, symbol: str
        ) -> list[dict[str, object]]:
            self.calls.append(("limit", side, price, qty, time_in_force, symbol))
            return []

        def place_market_order(self, side: str, qty: int, symbol: str) -> list[dict[str, object]]:
            self.calls.append(("market", side, qty, symbol))
            return []

    engine = FakeEngine()

    execute_command(engine, LimitOrderCommand(side="BUY", price=100, qty=1))
    execute_command(engine, MarketOrderCommand(side="SELL", qty=2))

    assert engine.calls == [
        ("limit", "Bid", 100, 1, "GTC", "DEFAULT"),
        ("market", "Ask", 2, "DEFAULT"),
    ]


def test_snapshot_default_and_symbol_specific_views() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    engine.place_limit_order("Bid", 100, 2, "GTC", "AAA")
    engine.place_limit_order("Ask", 101, 3, "GTC", "AAA")
    engine.place_limit_order("Ask", 99, 1, "GTC", "BBB")

    default_snapshot = engine.snapshot(5)
    assert default_snapshot["symbol"] == "DEFAULT"
    assert default_snapshot["bids"] == []
    assert default_snapshot["asks"] == []

    aaa_snapshot = engine.snapshot(5, "AAA")
    assert aaa_snapshot["symbol"] == "AAA"
    assert aaa_snapshot["sequence_number"] == 2
    assert aaa_snapshot["bids"][0]["price"] == 100
    assert aaa_snapshot["asks"][0]["price"] == 101

    bbb_snapshot = engine.snapshot(5, "BBB")
    assert len(bbb_snapshot["asks"]) == 1
    assert bbb_snapshot["asks"][0]["symbol"] == "BBB"
