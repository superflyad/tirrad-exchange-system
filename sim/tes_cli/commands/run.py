"""TES CLI strategy-driven simulation command."""

from __future__ import annotations

import argparse
from importlib import import_module

from sim.tes_models.commands import TesCommand
from sim.tes_models.events import (
    CancelRejectedEvent,
    OrderAcceptedEvent,
    OrderRejectedEvent,
    TradeExecutedEvent,
)
from sim.tes_strategy.registry import get_strategy


def _print_book_depth(depth: dict[str, list[dict[str, int]]]) -> None:
    bids = depth.get("bids", [])
    asks = depth.get("asks", [])

    print("Book Depth")
    print("----------")
    if bids:
        print("Bids:")
        for level in bids:
            print(f"price={level['price']} qty={level['qty']}")
    else:
        print("Bids: <empty>")

    print()

    if asks:
        print("Asks:")
        for level in asks:
            print(f"price={level['price']} qty={level['qty']}")
    else:
        print("Asks: <empty>")


def _format_command(command: TesCommand) -> str:
    if hasattr(command, "side"):
        return (
            "LimitOrder("
            f"side={command.side}, "
            f"price={command.price}, "
            f"qty={command.qty}"
            ")"
        )
    return f"CancelOrder(order_id={command.order_id})"


def _format_event(event: object) -> str:
    if isinstance(event, OrderAcceptedEvent):
        return (
            "OrderAccepted("
            f"order_id={event.data.order_id}, "
            f"side={event.data.side}, "
            f"price={event.data.price}, "
            f"qty={event.data.qty}"
            ")"
        )
    if isinstance(event, OrderRejectedEvent):
        return (
            "OrderRejected("
            f"side={event.data.side}, "
            f"price={event.data.price}, "
            f"qty={event.data.qty}, "
            f"reason={event.data.reason}"
            ")"
        )
    if isinstance(event, CancelRejectedEvent):
        return (
            "CancelRejected("
            f"order_id={event.data.order_id}, "
            f"reason={event.data.reason}"
            ")"
        )
    if isinstance(event, TradeExecutedEvent):
        return (
            "TradeExecuted("
            f"price={event.data.price}, "
            f"qty={event.data.qty}, "
            f"maker_order_id={event.data.maker_order_id}, "
            f"taker_order_id={event.data.taker_order_id}"
            ")"
        )
    return str(event)


def handle_run(args: argparse.Namespace) -> int:
    """Execute a strategy-driven simulation run and print summary."""
    try:
        strategy = get_strategy(args.strategy)
    except ValueError as exc:
        print(str(exc))
        return 1

    verbose = bool(getattr(args, "verbose", False))
    depth_levels = int(getattr(args, "depth_levels", 5))
    if depth_levels < 0:
        print("--depth-levels must be >= 0")
        return 1

    tes_engine = import_module("tes_engine")
    engine = tes_engine.MatchingEngine()
    all_events: list[object] = []

    pending_commands: list[TesCommand] = list(strategy.on_start())

    print("TES Strategy Run")
    print("----------------")
    print(f"Strategy: {args.strategy}")

    if verbose:
        print("Commands from strategy.on_start():")
        for command in pending_commands:
            print(f"- {_format_command(command)}")

    while pending_commands:
        command = pending_commands.pop(0)
        from sim.tes_simulation.runner import execute_command

        command_events = execute_command(engine, command)
        all_events.extend(command_events)

        for event in command_events:
            follow_up_commands = strategy.on_event(event)
            pending_commands.extend(follow_up_commands)

    if verbose:
        print("Event Stream:")
        for event in all_events:
            print(f"- {_format_event(event)}")

        print()
        depth_method = getattr(engine, "depth", None)
        if depth_method is None:
            print("Book Depth")
            print("----------")
            print("<unavailable>")
        else:
            _print_book_depth(depth_method(depth_levels))

    trade_events = [event for event in all_events if isinstance(event, TradeExecutedEvent)]
    total_trades = len(trade_events)
    total_traded_qty = sum(event.data.qty for event in trade_events)
    traded_notional = sum(event.data.price * event.data.qty for event in trade_events)

    print(f"Total Events: {len(all_events)}")
    print(f"Total Trades: {total_trades}")
    print(f"Total Traded Qty: {total_traded_qty}")
    print(f"Traded Notional: {traded_notional}")
    return 0
