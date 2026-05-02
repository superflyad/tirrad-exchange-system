"""TES CLI save command implementation."""

from __future__ import annotations

import argparse
from pathlib import Path

import tes_engine
from sim.tes_models.commands import LimitOrderCommand
from sim.tes_persistence.runs import save_run
from sim.tes_run import create_run_id
from sim.tes_simulation.runner import run_simulation

_DEFAULT_RUNS_DIR = Path("out") / "runs"


def run_save_command(base_dir: Path = _DEFAULT_RUNS_DIR) -> Path:
    """Run the demo simulation and persist it to a generated run directory."""
    engine = tes_engine.MatchingEngine()
    commands = [
        LimitOrderCommand(side="BUY", price=100, qty=10),
        LimitOrderCommand(side="SELL", price=100, qty=5),
    ]
    result = run_simulation(engine, commands)

    run_id = create_run_id(prefix="sim")
    metadata = {
        "run_id": run_id,
        "summary": {
            "total_commands": result.total_commands,
            "total_events": result.total_events,
        },
    }

    run_dir = save_run(base_dir=base_dir, run_id=run_id, events=result.events, metadata=metadata)
    print("Run saved:")
    print(run_dir)
    return run_dir


def handle_save(_args: argparse.Namespace) -> int:
    """CLI handler for `./tes sim save`."""
    run_save_command()
    return 0
