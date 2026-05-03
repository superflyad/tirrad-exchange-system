"""TES CLI strategy-driven simulation command."""

from __future__ import annotations

import argparse

import tes_engine
from sim.tes_models.commands import TesCommand
from sim.tes_simulation.runner import execute_command
from sim.tes_strategy.registry import get_strategy


def handle_run(args: argparse.Namespace) -> int:
    """Execute a strategy-driven simulation run and print summary."""
    try:
        strategy = get_strategy(args.strategy)
    except ValueError as exc:
        print(str(exc))
        return 1

    engine = tes_engine.MatchingEngine()
    all_events: list = []

    pending_commands: list[TesCommand] = list(strategy.on_start())

    while pending_commands:
        command = pending_commands.pop(0)
        command_events = execute_command(engine, command)
        all_events.extend(command_events)

        for event in command_events:
            follow_up_commands = strategy.on_event(event)
            pending_commands.extend(follow_up_commands)

    total_trades = sum(1 for event in all_events if event.type == "TradeExecuted")

    print("TES Strategy Run")
    print("----------------")
    print(f"Strategy: {args.strategy}")
    print(f"Total Events: {len(all_events)}")
    print(f"Total Trades: {total_trades}")
    return 0
