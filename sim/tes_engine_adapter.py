from __future__ import annotations

from typing import Any

from sim.tes_models import TesEvent, parse_events
from sim.tes_models.commands import CancelOrderCommand, LimitOrderCommand, TesCommand


def execute_command(engine: Any, command: TesCommand) -> list[TesEvent]:
    if isinstance(command, LimitOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        return parse_events(engine.place_limit_order(side, command.price, command.qty))

    if isinstance(command, CancelOrderCommand):
        return parse_events(engine.cancel(command.order_id))

    raise TypeError(f"unsupported command type: {type(command).__name__}")


def execute_commands(engine: Any, commands: list[TesCommand]) -> list[TesEvent]:
    events: list[TesEvent] = []
    for command in commands:
        events.extend(execute_command(engine, command))
    return events
