"""TES CLI inspect command."""

from __future__ import annotations

from pathlib import Path

from sim.tes_analytics import count_trades
from sim.tes_persistence.runs import load_run


def handle_inspect(args: object) -> int:
    run_id = getattr(args, "run_id")
    runs_dir = Path(getattr(args, "runs_dir"))

    events, _metadata = load_run(base_dir=runs_dir, run_id=run_id)

    print(f"Total Events: {len(events)}")
    print(f"Total Trades: {count_trades(events)}")

    return 0
