from __future__ import annotations

from sim.tes_simulation.runner import run_commands, run_simulation
from sim.tes_models.commands import CancelOrderCommand, LimitOrderCommand


def test_run_single_limit_order() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    result = run_simulation(engine, [LimitOrderCommand(side="BUY", price=100, qty=10)])

    assert any(event.type == "OrderAccepted" for event in result.events)


def test_run_crossing_orders() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    result = run_simulation(
        engine,
        [
            LimitOrderCommand(side="BUY", price=100, qty=10),
            LimitOrderCommand(side="SELL", price=100, qty=5),
        ],
    )

    assert any(event.type == "TradeExecuted" for event in result.events)


def test_run_cancel_order() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    placed = run_commands(engine, [LimitOrderCommand(side="BUY", price=100, qty=10)])
    accepted = next(event for event in placed if event.type == "OrderAccepted")

    result = run_simulation(engine, [CancelOrderCommand(order_id=accepted.data.order_id)])

    assert any(event.type == "OrderCanceled" for event in result.events)


def test_simulation_result_counts() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    commands = [LimitOrderCommand(side="BUY", price=100, qty=10)]

    result = run_simulation(engine, commands)

    assert result.total_commands == len(commands)
    assert result.total_events > 0


def test_multiple_commands_execution() -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    commands = [
        LimitOrderCommand(side="SELL", price=101, qty=10),
        LimitOrderCommand(side="BUY", price=101, qty=5),
        LimitOrderCommand(side="BUY", price=99, qty=3),
    ]

    events = run_commands(engine, commands)

    assert len(events) > 0
    assert any(event.type == "OrderAccepted" for event in events)
    assert any(event.type == "TradeExecuted" for event in events)
