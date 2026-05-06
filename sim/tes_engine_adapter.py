from __future__ import annotations

from typing import Any

from sim.tes_models import TesEngineEvent, parse_events
from sim.tes_models.commands import (
    CancelOrderCommand,
    ClearPriceBandsCommand,
    HaltSymbolCommand,
    LimitOrderCommand,
    HiddenOrderCommand,
    IcebergOrderCommand,
    MarketOrderCommand,
    ReplaceOrderCommand,
    SetPriceBandsCommand,
    SetTradingPhaseCommand,
    ResumeSymbolCommand,
    StopLimitOrderCommand,
    StopOrderCommand,
    TesCommand,
    UncrossAuctionCommand,
)


def execute_command(engine: Any, command: TesCommand) -> list[TesEngineEvent]:
    if isinstance(command, LimitOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        return parse_events(
            engine.place_limit_order(side, command.price, command.qty, command.time_in_force, command.symbol)
        )

    if isinstance(command, HiddenOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        return parse_events(engine.place_hidden_order(side, command.price, command.qty, command.symbol))

    if isinstance(command, IcebergOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        return parse_events(engine.place_iceberg_order(side, command.price, command.total_qty, command.display_qty, command.symbol))

    if isinstance(command, MarketOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        return parse_events(engine.place_market_order(side, command.qty, command.symbol))

    if isinstance(command, StopOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        return parse_events(engine.place_stop_order(side, command.stop_price, command.qty, command.symbol))

    if isinstance(command, StopLimitOrderCommand):
        side = "Bid" if command.side == "BUY" else "Ask"
        return parse_events(
            engine.place_stop_limit_order(side, command.stop_price, command.limit_price, command.qty, command.symbol)
        )

    if isinstance(command, CancelOrderCommand):
        return parse_events(engine.cancel(command.order_id))

    if isinstance(command, ReplaceOrderCommand):
        return parse_events(engine.replace_order(command.order_id, command.price, command.qty))

    if isinstance(command, SetTradingPhaseCommand):
        return parse_events(engine.set_trading_phase(command.symbol, command.phase))

    if isinstance(command, HaltSymbolCommand):
        return parse_events(engine.halt_symbol(command.symbol, command.reason))

    if isinstance(command, ResumeSymbolCommand):
        return parse_events(engine.resume_symbol(command.symbol))

    if isinstance(command, SetPriceBandsCommand):
        return parse_events(engine.set_price_bands(command.symbol, command.lower_price, command.upper_price))

    if isinstance(command, ClearPriceBandsCommand):
        return parse_events(engine.clear_price_bands(command.symbol))

    if isinstance(command, UncrossAuctionCommand):
        return parse_events(engine.uncross(command.symbol))

    raise TypeError(f"unsupported command type: {type(command).__name__}")


def execute_commands(engine: Any, commands: list[TesCommand]) -> list[TesEngineEvent]:
    events: list[TesEngineEvent] = []
    for command in commands:
        events.extend(execute_command(engine, command))
    return events
