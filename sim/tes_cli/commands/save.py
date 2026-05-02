from __future__ import annotations

from pathlib import Path

from sim.tes_models.commands import LimitOrderCommand
from sim.tes_persistence.runs import save_run
from sim.tes_run.ids import create_run_id, validate_run_id
from sim.tes_simulation.results import build_run_record
from sim.tes_simulation.runner import run_simulation

DEFAULT_RUNS_DIR = Path("out") / "runs"


def run_save_command(base_dir: Path = DEFAULT_RUNS_DIR, run_id: str | None = None) -> Path:
    """Run a deterministic demo simulation, persist the run, and return the run directory."""
    import tes_engine

    engine = tes_engine.MatchingEngine()
    commands = [
        LimitOrderCommand(side="BUY", price=100, qty=10),
        LimitOrderCommand(side="SELL", price=100, qty=5),
    ]

    result = run_simulation(engine=engine, commands=commands)
    resolved_run_id = validate_run_id(run_id) if run_id is not None else create_run_id(prefix="sim")

    run_record = build_run_record(
        run_id=resolved_run_id,
        events=result.events,
        total_commands=result.total_commands,
    )

    metadata = {
        "run_id": run_record.run_id,
        "summary": {
            "total_commands": run_record.summary.total_commands,
            "total_events": run_record.summary.total_events,
            "total_trades": run_record.summary.total_trades,
            "total_order_accepted": run_record.summary.total_order_accepted,
            "total_order_canceled": run_record.summary.total_order_canceled,
        },
    }

    run_dir = save_run(
        base_dir=base_dir,
        run_id=run_record.run_id,
        events=run_record.events,
        metadata=metadata,
    )

    print(f"Run saved: {run_dir}")
    return run_dir
