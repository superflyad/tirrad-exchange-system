from __future__ import annotations

import importlib
from pathlib import Path

from sim.tes_models.commands import LimitOrderCommand, TesCommand
from sim.tes_models.events import TesEvent
from sim.tes_persistence.runs import load_run, save_run
from sim.tes_simulation.runner import run_simulation


def test_tes_persistence_integration_smoke(tmp_path: Path) -> None:
    import tes_engine

    engine = tes_engine.MatchingEngine()
    commands: list[TesCommand] = [
        LimitOrderCommand(side="BUY", price=100, qty=10),
        LimitOrderCommand(side="SELL", price=100, qty=5),
    ]

    simulation_result = run_simulation(engine, commands)
    original_events: list[TesEvent] = simulation_result.events

    assert any(event.type == "TradeExecuted" for event in original_events)

    run_id = "integration-smoke"
    metadata = {
        "run_id": run_id,
        "summary": {
            "total_commands": simulation_result.total_commands,
            "total_events": simulation_result.total_events,
        },
    }

    save_run(base_dir=tmp_path, run_id=run_id, events=original_events, metadata=metadata)
    loaded_events, _ = load_run(base_dir=tmp_path, run_id=run_id)

    assert len(loaded_events) == len(original_events)

    if importlib.util.find_spec("sim.tes_replay") is not None:
        from sim.tes_replay import replay_events

        replay_result = replay_events(loaded_events)
        assert replay_result.total_events == len(loaded_events)
