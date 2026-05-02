from __future__ import annotations

from pathlib import Path

from sim.tes_persistence.runs import load_run
from sim.tes_replay import replay_events

DEFAULT_RUNS_DIR = Path("out") / "runs"


def replay_saved_run(run_id: str, base_dir: Path = DEFAULT_RUNS_DIR) -> int:
    events, _metadata = load_run(base_dir=base_dir, run_id=run_id)
    result = replay_events(events)

    print("Replay Complete")
    print(f"Total Events: {result.total_events}")

    return 0
