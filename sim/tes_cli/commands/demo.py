"""TES CLI demo simulation command."""

from __future__ import annotations

import argparse

import tes_engine
from sim.tes_models.commands import LimitOrderCommand, TesCommand
from sim.tes_simulation.runner import run_simulation


def add_demo_command(sim_subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the ``sim demo`` command."""
    demo_parser = sim_subparsers.add_parser("demo", help="Run deterministic TES demo simulation")
    demo_parser.set_defaults(handler=handle_demo)


def handle_demo(_args: argparse.Namespace) -> int:
    """Execute a deterministic two-order crossing simulation and print summary."""
    engine = tes_engine.MatchingEngine()
    commands: list[TesCommand] = [
        LimitOrderCommand(side="BUY", price=101, qty=10),
        LimitOrderCommand(side="SELL", price=100, qty=10),
    ]
    result = run_simulation(engine, commands)
    total_trades = sum(1 for event in result.events if event.type == "TradeExecuted")

    print("TES Demo Run")
    print("------------")
    print(f"Total Events: {result.total_events}")
    print(f"Total Trades: {total_trades}")
    return 0
