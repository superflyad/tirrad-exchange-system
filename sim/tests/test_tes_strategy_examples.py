from __future__ import annotations

from sim.tes_models.commands import LimitOrderCommand
from sim.tes_strategy.examples import CrossingTakerStrategy


def test_crossing_taker_on_start_returns_two_commands() -> None:
    strategy = CrossingTakerStrategy()

    commands = strategy.on_start()

    assert len(commands) == 2
    assert all(isinstance(command, LimitOrderCommand) for command in commands)


def test_crossing_taker_second_command_crosses_first_by_price() -> None:
    strategy = CrossingTakerStrategy()

    first_command, second_command = strategy.on_start()

    assert isinstance(first_command, LimitOrderCommand)
    assert isinstance(second_command, LimitOrderCommand)
    assert first_command.side == "BUY"
    assert second_command.side == "SELL"
    assert second_command.price <= first_command.price


def test_crossing_taker_on_event_returns_empty_commands() -> None:
    strategy = CrossingTakerStrategy()

    assert strategy.on_event(event=object()) == []
