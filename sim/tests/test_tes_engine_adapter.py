from __future__ import annotations

import pytest

from sim.tes_engine_adapter import execute_command, execute_commands
from sim.tes_models.commands import CancelOrderCommand, LimitOrderCommand, MarketOrderCommand


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

    events = execute_command(engine, MarketOrderCommand(side="BUY", qty=5))

    assert [event.type for event in events] == ["TradeExecuted", "OrderPartiallyFilled", "TopOfBook"]
    trade = events[0]
    partial = events[1]
    assert trade.data.price == 100
    assert trade.data.qty == 3
    assert partial.data.last_fill_qty == 3
    assert partial.data.remaining_qty == 2

