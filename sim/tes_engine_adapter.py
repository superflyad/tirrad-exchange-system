from __future__ import annotations

from typing import Any

from sim.tes_models import TesEngineEvent, parse_events
from sim.tes_models.commands import DEFAULT_SYMBOL, CancelOrderCommand, LimitOrderCommand, MarketOrderCommand, ReplaceOrderCommand, TesCommand


def execute_command(engine: Any, command: TesCommand) -> list[TesEngineEvent]:
    if isinstance(command, LimitOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        if command.symbol == DEFAULT_SYMBOL:
            return parse_events(engine.place_limit_order(side, command.price, command.qty, command.time_in_force))
        return parse_events(engine.place_limit_order(side, command.price, command.qty, command.time_in_force, command.symbol))

    if isinstance(command, MarketOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        if command.symbol == DEFAULT_SYMBOL:
            return parse_events(engine.place_market_order(side, command.qty))
        return parse_events(engine.place_market_order(side, command.qty, command.symbol))

    if isinstance(command, CancelOrderCommand):
        return parse_events(engine.cancel(command.order_id))

    if isinstance(command, ReplaceOrderCommand):
        return parse_events(engine.replace_order(command.order_id, command.price, command.qty))

    raise TypeError(f"unsupported command type: {type(command).__name__}")


def execute_commands(engine: Any, commands: list[TesCommand]) -> list[TesEngineEvent]:
    events: list[TesEngineEvent] = []
    for command in commands:
        events.extend(execute_command(engine, command))
    return events
